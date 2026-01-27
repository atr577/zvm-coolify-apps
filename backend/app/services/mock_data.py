"""
Mock data for testing without AIMLAPI
"""

MOCK_STORY = {
    "concept": "Модель в элегантном платье танцует под медленную музыку на фоне заката. Камера делает плавный круговой облет вокруг нее, подчеркивая изящество движений и игру света на ткани платья.",
    "theme": "Мода и красота",
    "target_audience": "Женщины 18-35 лет, интересующиеся модой и стилем жизни",
    "hook": "Неожиданная трансформация: модель начинает вращаться и ее платье превращается в вихрь света",
    "emotional_trigger": "Восхищение красотой и желание повторить",
    "viral_potential": "Сочетание визуальной эстетики, плавных движений камеры и магического эффекта создает завораживающий эффект, который зрители захотят пересматривать и показывать друзьям"
}

MOCK_DESCRIPTION = {
    "model": {
        "appearance": "Молодая женщина европейской внешности, длинные темные волосы, собранные в элегантную прическу",
        "clothing": "Длинное вечернее платье цвета индиго с блестками, струящаяся ткань",
        "pose": "Грациозные танцевальные движения, руки плавно поднимаются вверх, легкое вращение",
        "expression": "Загадочная улыбка, уверенный взгляд в камеру"
    },
    "environment": {
        "location": "Открытая терраса на крыше небоскреба",
        "time_of_day": "Золотой час, закат",
        "weather": "Ясная погода, легкий ветер",
        "atmosphere": "Романтическая, мечтательная атмосфера"
    },
    "composition": {
        "camera_angle": "Средний план, круговой облет вокруг модели",
        "lighting": "Естественное освещение заката, теплые золотистые тона, контровый свет создает сияние вокруг силуэта",
        "colors": "Теплая цветовая палитра: золотой, оранжевый, индиго, фиолетовый",
        "framing": "Модель в центре кадра, на заднем плане силуэты небоскребов и небо"
    }
}

MOCK_PROMPT = {
    "main_prompt": "A elegant young woman in a flowing indigo evening gown with sparkles dances gracefully on a rooftop terrace at golden hour sunset, long dark hair in elegant updo, mysterious smile, confident gaze, arms rising gracefully, gentle spin, cinematic circular camera movement orbiting around her, warm golden lighting, backlit silhouette with glowing halo effect, city skyline in background, romantic dreamy atmosphere, 8k, ultra detailed, fashion photography style",
    "style_suffix": "cinematic lighting, shallow depth of field, professional fashion photography",
    "negative_prompt": "blurry, low quality, distorted, deformed, ugly, bad anatomy, extra limbs, poorly drawn face, dull colors, overexposed, underexposed, static shot, bad lighting",
    "recommended_aspect_ratio": "9:16"
}

MOCK_IMAGE_URL = "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400&h=711&fit=crop"

MOCK_SCENARIO = {
    "motion_prompt": "Woman dances gracefully, arms rising, gentle spin, dress flowing with movement, glowing light effect builds",
    "camera_movement": {
        "type": "orbit",
        "speed": "slow",
        "description": "Плавный круговой облет вокруг модели"
    },
    "subject_action": "Модель танцует, поднимает руки и вращается",
    "key_moments": [
        {"timestamp": "0.0-2.0s", "action": "Модель стоит с закрытыми глазами, руки опущены"},
        {"timestamp": "2.0-4.0s", "action": "Открывает глаза, начинает вращаться, платье светится"},
        {"timestamp": "4.0-5.0s", "action": "Финальная улыбка, платье превращается в вихрь света"}
    ]
}

MOCK_VIDEO_URL = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"

MOCK_ADAPTATIONS = {
    "instagram": {
        "caption": "✨ Когда закат превращает обычный момент в магию ✨\n\n#fashion #sunset #magic #reels #instafashion #style #beauty #goldenhour #dreamy #viral",
        "hashtags": ["fashion", "sunset", "magic", "reels", "instafashion", "style", "beauty", "goldenhour", "dreamy", "viral"],
        "format": "9:16 вертикальное видео",
        "duration": "5 секунд",
        "cover_frame": "Кадр с полным свечением платья (4 секунда)",
        "posting_tips": "Публиковать в 19:00-21:00 по местному времени для максимального охвата"
    },
    "tiktok": {
        "caption": "Вечерняя магия ✨ #fashion #sunset #fyp #viral",
        "hashtags": ["fashion", "sunset", "fyp", "viral", "foryou", "magic", "style"],
        "format": "9:16 вертикальное видео",
        "duration": "5 секунд",
        "sound_recommendation": "Trending slow-motion music track",
        "effects": "Добавить эффект 'Bling' в TikTok на момент свечения",
        "posting_tips": "Публиковать в 18:00-20:00, использовать trending sound"
    },
    "youtube": {
        "title": "Магическая трансформация: Закат и мода | Fashion Magic #Shorts",
        "description": "Захватывающий момент, когда закат превращает обычное платье в произведение искусства. \n\n#Shorts #Fashion #Sunset #Magic #Style",
        "tags": ["fashion", "sunset", "magic", "style", "beauty", "shorts", "viral", "dress", "transformation"],
        "format": "9:16 вертикальное видео",
        "duration": "5 секунд",
        "thumbnail": "Кадр со свечением платья с наложенным текстом 'MAGIC'",
        "posting_tips": "Добавить в плейлист Fashion Shorts, публиковать утром 10:00-12:00"
    }
}

MOCK_VALIDATION_RESULT = {
    "status": "pass",
    "score": 92,
    "criteria_results": {
        "Соответствие техническому заданию": {
            "score": 95,
            "comment": "Полностью соответствует заданной концепции"
        },
        "Виральный потенциал": {
            "score": 90,
            "comment": "Высокий потенциал благодаря визуальным эффектам и эмоциональному воздействию"
        },
        "Качество исполнения": {
            "score": 92,
            "comment": "Отличное качество, профессиональный подход"
        }
    },
    "warnings": [],
    "errors": [],
    "recommendations": [
        "Рассмотреть добавление музыкального сопровождения для усиления эмоционального эффекта",
        "Можно добавить текстовый overlay в первой секунде для увеличения hook"
    ]
}
