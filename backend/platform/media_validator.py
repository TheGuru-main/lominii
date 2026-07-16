# platform/media_validator.py

MB = 1024 * 1024

MEDIA_RULES = {

    # ==========================================================
    # SOCIAL COMMENTS
    # ==========================================================
    "social_comment": {

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

    # ==========================================================
    # SOCIAL POSTS
    # ==========================================================
    "social_post": {

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

    # ==========================================================
    # SOCIAL STATUS
    # ==========================================================
    "social_status": {

        "image": {
            "max_size": 10 * MB,
        },

        "voice": {
            "max_size": 10 * MB,
            "max_duration": 120,
        },

        "video": {
            "max_size": 100 * MB,
            "max_duration": 120,
        },
    },

    # ==========================================================
    # MESSAGING
    # (Social, Communities, Organizations, Games, Marketplace)
    # ==========================================================
    "messaging": {

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

    # ==========================================================
    # EDUCATION
    # ==========================================================
    "education": {

        "image": {
            "max_size": 20 * MB,
        },

        "voice": {
            "max_size": 20 * MB,
            "max_duration": 3600,
        },

        "video": {
            "max_size": 1024 * MB,
            "max_duration": 7200,
        },

        "file": {
            "max_size": 1024 * MB,
        },
    },
}

from fastapi import HTTPException


def validate_profile(profile: str):
    if profile not in MEDIA_RULES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown media profile: {profile}",
        )

def validate_media_type(
    profile: str,
    media_type: str,
):
    validate_profile(profile)

    if media_type not in MEDIA_RULES[profile]:
        raise HTTPException(
            status_code=400,
            detail=f"{media_type} is not allowed for {profile}.",
        )

def validate_media_size(
    profile: str,
    media_type: str,
    size: int,
):
    limit = MEDIA_RULES[profile][media_type]["max_size"]

    if size > limit:
        raise HTTPException(
            status_code=400,
            detail="Media file exceeds the allowed size.",
        )