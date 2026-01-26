"""
Hook Analyzer - Find best audio hooks using FFmpeg beat/energy detection.

Analyzes music tracks to find high-energy segments for short-form video content.
No AI required - uses audio signal analysis.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, asdict
from typing import List, Optional, Tuple

from app.core.config import settings
from app.core.media_processor import media_processor

logger = logging.getLogger(__name__)


@dataclass
class Hook:
    """Represents a hook segment in an audio track."""

    start: float  # Start time in seconds
    end: float  # End time in seconds
    duration: float  # Duration (end - start)
    reason: str  # Why this is a good hook
    energy: str  # Energy level: low, medium, high
    type: str  # Hook type: chorus, drop, bridge, intro, etc.

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class HookAnalyzer:
    """Analyzes audio to find best hooks using FFmpeg energy detection."""

    def __init__(self):
        """Initialize hook analyzer."""
        logger.info("HookAnalyzer: Using FFmpeg beat detection")

    async def find_hooks(
        self,
        audio_path: str,
        video,
        num_hooks: int = 4,
        hook_duration: float = 5.0,
    ) -> List[Hook]:
        """
        Find best hooks in an audio track using energy analysis.

        Args:
            audio_path: Path to the audio file
            video: Video model instance (for context)
            num_hooks: Number of hooks to find
            hook_duration: Duration of each hook in seconds

        Returns:
            List of Hook objects sorted by energy (highest first)
        """
        try:
            # Get total duration
            total_duration = await media_processor.get_audio_duration(audio_path)
            logger.info(f"Analyzing audio: {audio_path} ({total_duration:.1f}s)")

            # Find high-energy moments using FFmpeg
            energy_peaks = await self._find_energy_peaks(
                audio_path, total_duration, num_hooks, hook_duration
            )

            if not energy_peaks:
                logger.warning("No energy peaks found, using fallback")
                return self._create_fallback_hooks(total_duration, hook_duration, num_hooks)

            # Convert peaks to hooks
            hooks = []
            for i, (start_time, energy_level) in enumerate(energy_peaks):
                end_time = min(start_time + hook_duration, total_duration)

                # Determine energy label
                if energy_level > 0.7:
                    energy = "high"
                    hook_type = "drop" if i == 0 else "chorus"
                elif energy_level > 0.4:
                    energy = "medium"
                    hook_type = "verse"
                else:
                    energy = "low"
                    hook_type = "bridge"

                hooks.append(Hook(
                    start=start_time,
                    end=end_time,
                    duration=end_time - start_time,
                    reason=f"High energy segment (peak {i+1})",
                    energy=energy,
                    type=hook_type,
                ))

            # Sort by energy level (high first)
            energy_order = {"high": 0, "medium": 1, "low": 2}
            hooks.sort(key=lambda h: energy_order.get(h.energy, 1))

            logger.info(f"Found {len(hooks)} hooks via beat detection")
            for i, h in enumerate(hooks):
                logger.debug(f"  Hook {i+1}: {h.start:.1f}-{h.end:.1f}s ({h.type}, {h.energy})")

            return hooks

        except Exception as e:
            logger.error(f"Hook analysis failed: {e}")
            return self._create_fallback_hooks(total_duration, hook_duration, num_hooks)

    async def _find_energy_peaks(
        self,
        audio_path: str,
        total_duration: float,
        num_peaks: int,
        hook_duration: float,
    ) -> List[Tuple[float, float]]:
        """
        Find high-energy moments in audio using FFmpeg.

        Uses astats filter to measure RMS energy in segments.

        Returns:
            List of (start_time, normalized_energy) tuples
        """
        # Analyze audio in segments
        segment_duration = 2.0  # Analyze 2-second windows
        segments = []

        # Calculate RMS for each segment
        for start in range(0, int(total_duration - hook_duration), int(segment_duration)):
            try:
                # Use FFmpeg to get RMS level for this segment
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start),
                    "-t", str(segment_duration),
                    "-i", audio_path,
                    "-af", "astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level",
                    "-f", "null", "-"
                ]

                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await process.communicate()

                # Parse RMS level from output
                stderr_text = stderr.decode()
                rms_match = re.search(r'RMS_level=(-?[\d.]+)', stderr_text)

                if rms_match:
                    rms_db = float(rms_match.group(1))
                    # Convert dB to linear (0-1 range, roughly)
                    # RMS typically -60 to 0 dB
                    normalized = max(0, min(1, (rms_db + 60) / 60))
                    segments.append((float(start), normalized))

            except Exception as e:
                logger.debug(f"Error analyzing segment at {start}s: {e}")
                continue

        if not segments:
            return []

        # Sort by energy (highest first) and pick top N
        segments.sort(key=lambda x: x[1], reverse=True)

        # Filter to avoid overlapping hooks
        selected = []
        for start, energy in segments:
            # Check if this segment overlaps with already selected
            overlaps = False
            for sel_start, _ in selected:
                if abs(start - sel_start) < hook_duration:
                    overlaps = True
                    break

            if not overlaps:
                selected.append((start, energy))
                if len(selected) >= num_peaks:
                    break

        return selected

    def _create_fallback_hooks(
        self,
        total_duration: float,
        hook_duration: float,
        num_hooks: int = 1,
    ) -> List[Hook]:
        """
        Create fallback hooks evenly distributed across the track.
        """
        logger.info("Creating fallback hooks (distributed)")

        hooks = []

        if total_duration <= hook_duration:
            # Track shorter than hook - use whole track
            hooks.append(Hook(
                start=0.0,
                end=total_duration,
                duration=total_duration,
                reason="Full track (short audio)",
                energy="medium",
                type="full",
            ))
        else:
            # Distribute hooks across the track
            # Start from 10% into the track (skip intro)
            usable_duration = total_duration - hook_duration
            start_offset = min(usable_duration * 0.1, 5.0)  # Skip first 10% or 5s

            if num_hooks == 1:
                # Single hook - start from beginning or slight offset
                start = start_offset
                hooks.append(Hook(
                    start=start,
                    end=start + hook_duration,
                    duration=hook_duration,
                    reason="Start of track",
                    energy="medium",
                    type="intro",
                ))
            else:
                # Multiple hooks - distribute evenly
                interval = usable_duration / num_hooks
                for i in range(num_hooks):
                    start = start_offset + (i * interval)
                    start = min(start, total_duration - hook_duration)

                    hooks.append(Hook(
                        start=start,
                        end=start + hook_duration,
                        duration=hook_duration,
                        reason=f"Segment {i+1}",
                        energy="medium",
                        type="verse" if i > 0 else "intro",
                    ))

        return hooks


# Singleton instance
hook_analyzer = HookAnalyzer()
