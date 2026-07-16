# platform/media_validator.py

MB = 1024 * 1024

MEDIA_RULES = {

    # Social comments
    "comment": {
        "image": {
            "max_size": 5 * MB,
        },
        "gif": {
            "max_size": 10 * MB,
        },
        "voice": {
            "max_size": 5 * MB,
            "max_duration": 120,
        },
        "video": {
            "max_size": 2 * MB,
            "max_duration": 120,
        },
        "file": {
            "max_size": 5 * MB,
        },
    },

    # Social posts
    "post": {
        "image": {
            "max_size": 20 * MB,
        },
        "gif": {
            "max_size": 20 * MB,
        },
        "voice": {
            "max_size": 20 * MB,
            "max_duration": 600,
        },
        "video": {
            "max_size": 500 * MB,
            "max_duration": 1800,
        },
        "file": {
            "max_size": 50 * MB,
        },
    },

    # Chats (Social, Community, Org AI, Games)
    "chat": {
        "image": {
            "max_size": 10 * MB,
        },
        "gif": {
            "max_size": 10 * MB,
        },
        "voice": {
            "max_size": 10 * MB,
            "max_duration": 300,
        },
        "video": {
            "max_size": 100 * MB,
            "max_duration": 900,
        },
        "file": {
            "max_size": 20 * MB,
        },
    },

    # Status/Stories
    "status": {
        "image": {
            "max_size": 10 * MB,
        },
        "video": {
            "max_size": 100 * MB,
            "max_duration": 120,
        },
        "voice": {
            "max_size": 10 * MB,
            "max_duration": 120,
        },
    },

    # Education
    "edu": {
        "image": {
            "max_size": 20 * MB,
        },
        "video": {
            "max_size": 1024 * MB,
            "max_duration": 7200,
        },
        "voice": {
            "max_size": 20 * MB,
            "max_duration": 3600,
        },
        "file": {
            "max_size": 1024 * MB,
        },
    },
}