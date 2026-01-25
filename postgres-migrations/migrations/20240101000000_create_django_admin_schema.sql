-- Migration: Create django_admin schema and telegram_channels table
-- Timestamp: 20240101000000

-- Create schema
CREATE SCHEMA IF NOT EXISTS django_admin;

-- Create telegram_channels table
CREATE TABLE IF NOT EXISTS django_admin.telegram_channels (
    name TEXT NOT NULL
);

-- Add comment
COMMENT ON SCHEMA django_admin IS 'Schema for Django admin interface';
COMMENT ON TABLE django_admin.telegram_channels IS 'Table storing telegram channel names';
