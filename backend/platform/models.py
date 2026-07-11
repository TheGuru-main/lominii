"""SQLAlchemy ORM Models – all LOMINII schemas"""
import uuid
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Boolean, JSON, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from platform.database import Base

# ===========================================================================
# PUBLIC (shared)
# ===========================================================================
class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    google_id = Column(String(255), unique=True)
    phone = Column(String(20), unique=True)
    occupation = Column(String(100))
    language = Column(String(10), default="en")
    news_preferences = Column(JSONB)
    subscription_status = Column(String(20), default="free")
    role = Column(String(20), default="user")
    created_at = Column(DateTime, server_default="now()")

# ===========================================================================
# SEARCH
# ===========================================================================
class Search(Base):
    __tablename__ = "searches"
    __table_args__ = {"schema": "search"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"))
    query = Column(Text, nullable=False)
    gsp_cell = Column(String(10))
    created_at = Column(DateTime, server_default="now()")

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = {"schema": "search"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"))
    to_user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"))
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default="now()")

class Trending(Base):
    __tablename__ = "trending"
    __table_args__ = {"schema": "search"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    count = Column(Integer, default=1)
    updated_at = Column(DateTime, server_default="now()")

class Correction(Base):
    __tablename__ = "corrections"
    __table_args__ = {"schema": "search"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    misspelled = Column(Text, nullable=False)
    corrected = Column(Text, nullable=False)
    gsp_cell = Column(String(10))
    confidence = Column(Float, default=0.0)

class NewsArticle(Base):
    __tablename__ = "news_articles"
    __table_args__ = {"schema": "search"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), nullable=False)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    source = Column(String(255))
    published_at = Column(DateTime)
    inserted_at = Column(DateTime, server_default="now()")

class NewsCache(Base):
    __tablename__ = "news_cache"
    __table_args__ = {"schema": "search"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(50), unique=True, nullable=False)
    articles = Column(JSONB, nullable=False)
    cached_at = Column(DateTime, server_default="now()")

class DictionaryCache(Base):
    __tablename__ = "dictionary_cache"
    __table_args__ = {"schema": "search"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(255), unique=True, nullable=False)
    definition = Column(Text, nullable=False)
    language = Column(String(10), default="en")
    cached_at = Column(DateTime, server_default="now()")

class SearchCache(Base):
    __tablename__ = "search_cache"
    __table_args__ = {"schema": "search"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(64), unique=True, nullable=False)
    result = Column(JSONB, nullable=False)
    cached_at = Column(DateTime, server_default="now()")

class VideoCache(Base):
    __tablename__ = "video_cache"
    __table_args__ = {"schema": "search"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(Text, nullable=False)
    videos = Column(JSONB, nullable=False)
    cached_at = Column(DateTime, server_default="now()")

# ===========================================================================
# SOCIAL
# ===========================================================================
class SocialProfile(Base):
    __tablename__ = "profiles"
    __table_args__ = {"schema": "social"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    core_user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)
    social_uid = Column(String(20), unique=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    bio = Column(Text)
    avatar_url = Column(Text)
    location = Column(String)          # PostGIS geography simplified
    created_at = Column(DateTime, server_default="now()")

class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = {"schema": "social"}
    follower_id = Column(UUID(as_uuid=True), ForeignKey("social.profiles.id"), primary_key=True)
    followee_id = Column(UUID(as_uuid=True), ForeignKey("social.profiles.id"), primary_key=True)
    created_at = Column(DateTime, server_default="now()")

class Post(Base):
    __tablename__ = "posts"
    __table_args__ = {"schema": "social"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(UUID(as_uuid=True), ForeignKey("social.profiles.id"), nullable=False)
    content = Column(Text, nullable=False)
    media_urls = Column(JSONB)
    visibility = Column(String(20), default="public")
    location = Column(String)
    created_at = Column(DateTime, server_default="now()")

class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = {"schema": "social"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey("social.posts.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(UUID(as_uuid=True), ForeignKey("social.profiles.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default="now()")

class Like(Base):
    __tablename__ = "likes"
    __table_args__ = {"schema": "social"}
    post_id = Column(UUID(as_uuid=True), ForeignKey("social.posts.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("social.profiles.id"), primary_key=True)
    created_at = Column(DateTime, server_default="now()")

class Community(Base):
    __tablename__ = "communities"
    __table_args__ = {"schema": "social"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_by = Column(UUID(as_uuid=True), ForeignKey("social.profiles.id"), nullable=False)
    created_at = Column(DateTime, server_default="now()")

class CommunityMember(Base):
    __tablename__ = "community_members"
    __table_args__ = {"schema": "social"}
    community_id = Column(UUID(as_uuid=True), ForeignKey("social.communities.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("social.profiles.id"), primary_key=True)
    role = Column(String(20), default="member")
    joined_at = Column(DateTime, server_default="now()")

class PrivacySettings(Base):
    __tablename__ = "privacy_settings"
    __table_args__ = {"schema": "social"}
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), primary_key=True)
    profile_visibility = Column(String(20), default="public")
    search_visibility = Column(String(20), default="public")
    friend_request_permission = Column(String(20), default="everyone")
    last_seen_visibility = Column(String(20), default="friends")
    created_at = Column(DateTime, server_default="now()")
    updated_at = Column(DateTime, server_default="now()")

class FriendRequest(Base):
    __tablename__ = "friend_requests"
    __table_args__ = {"schema": "social"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sender_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, server_default="now()")
    updated_at = Column(DateTime, server_default="now()")

class BlockedUser(Base):
    __tablename__ = "blocked_users"
    __table_args__ = {"schema": "social"}
    blocker_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), primary_key=True)
    blocked_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, server_default="now()")

class MutedUser(Base):
    __tablename__ = "muted_users"
    __table_args__ = {"schema": "social"}
    muter_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), primary_key=True)
    muted_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), primary_key=True)
    created_at = Column(DateTime, server_default="now()")

# ===========================================================================
# CURRICULUM (EDU)
# ===========================================================================
class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = {"schema": "curriculum"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)

class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = {"schema": "curriculum"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("curriculum.subjects.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)

class Subtopic(Base):
    __tablename__ = "subtopics"
    __table_args__ = {"schema": "curriculum"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    topic_id = Column(Integer, ForeignKey("curriculum.topics.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)

class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = {"schema": "curriculum"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    subtopic_id = Column(Integer, ForeignKey("curriculum.subtopics.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)

class Question(Base):
    __tablename__ = "questions"
    __table_args__ = {"schema": "curriculum"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    concept_id = Column(Integer, ForeignKey("curriculum.concepts.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(JSONB)
    correct_answer = Column(Text)
    difficulty = Column(String(20))
    exam_type = Column(String(20))
    year = Column(Integer)
    tags = Column(JSONB)

class KnowledgeLink(Base):
    __tablename__ = "knowledge_links"
    __table_args__ = {"schema": "curriculum"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    concept_id_1 = Column(Integer, ForeignKey("curriculum.concepts.id", ondelete="CASCADE"), nullable=False)
    concept_id_2 = Column(Integer, ForeignKey("curriculum.concepts.id", ondelete="CASCADE"), nullable=False)
    relationship = Column(String(50))

# ===========================================================================
# CLASSROOM (EDU)
# ===========================================================================
class Class(Base):
    __tablename__ = "classes"
    __table_args__ = {"schema": "classroom"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("curriculum.subjects.id"), nullable=False)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default="now()")

class ClassEnrollment(Base):
    __tablename__ = "class_enrollments"
    __table_args__ = {"schema": "classroom"}
    class_id = Column(UUID(as_uuid=True), ForeignKey("classroom.classes.id", ondelete="CASCADE"), primary_key=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), primary_key=True)
    joined_at = Column(DateTime, server_default="now()")

class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = {"schema": "classroom"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classroom.classes.id", ondelete="CASCADE"), nullable=False)
    concept_id = Column(Integer, ForeignKey("curriculum.concepts.id"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text)
    created_at = Column(DateTime, server_default="now()")

class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = {"schema": "classroom"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("classroom.lessons.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    due_date = Column(DateTime)
    created_at = Column(DateTime, server_default="now()")

class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = {"schema": "classroom"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("classroom.assignments.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text)
    submitted_at = Column(DateTime, server_default="now()")

# ===========================================================================
# ASSESSMENT (EDU)
# ===========================================================================
class ConceptMastery(Base):
    __tablename__ = "concept_mastery"
    __table_args__ = {"schema": "assessment"}
    student_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), primary_key=True)
    concept_id = Column(Integer, ForeignKey("curriculum.concepts.id", ondelete="CASCADE"), primary_key=True)
    mastery = Column(Float, default=0.0)
    last_practiced = Column(DateTime)

class QuestionLog(Base):
    __tablename__ = "question_logs"
    __table_args__ = {"schema": "assessment"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("curriculum.questions.id", ondelete="CASCADE"), nullable=False)
    chosen_answer = Column(Text)
    is_correct = Column(Boolean)
    answered_at = Column(DateTime, server_default="now()")

# ===========================================================================
# GAMES
# ===========================================================================
class GameSession(Base):
    __tablename__ = "game_sessions"
    __table_args__ = {"schema": "game"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id = Column(String(20), nullable=False)
    room_id = Column(String(20), unique=True, nullable=False)
    players = Column(JSONB, nullable=False)
    game_state = Column(JSONB)
    status = Column(String(20), default="waiting")
    created_at = Column(DateTime, server_default="now()")
    finished_at = Column(DateTime)

class Leaderboard(Base):
    __tablename__ = "leaderboards"
    __table_args__ = {"schema": "game"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String(20), nullable=False)
    user_email = Column(String(255), nullable=False)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    points = Column(Integer, default=1000)
    updated_at = Column(DateTime, server_default="now()")

# ===========================================================================
# ADS
# ===========================================================================
class PremiumSubscription(Base):
    __tablename__ = "premium_subscriptions"
    __table_args__ = {"schema": "ads"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"))
    tier = Column(String(20), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String(20), default="active")
    payment_reference = Column(Text)
    created_at = Column(DateTime, server_default="now()")

class SponsoredCell(Base):
    __tablename__ = "sponsored_cells"
    __table_args__ = {"schema": "ads"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    advertiser_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), nullable=False)
    col = Column(Integer, nullable=False)
    row = Column(Integer, nullable=False)
    ad_content = Column(JSONB)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    active = Column(Boolean, default=True)

# ===========================================================================
# ADMIN
# ===========================================================================
class Occupancy(Base):
    __tablename__ = "occupancy"
    __table_args__ = {"schema": "admin"}
    col = Column(Integer, primary_key=True)
    row = Column(Integer, primary_key=True)
    searches = Column(Integer, default=0)
    games = Column(Integer, default=0)
    users = Column(Integer, default=0)
    messages = Column(Integer, default=0)
    api_calls = Column(Integer, default=0)
    cache_hits = Column(Integer, default=0)

class UsernameCell(Base):
    __tablename__ = "username_cells"
    __table_args__ = {"schema": "admin"}
    col = Column(Integer, primary_key=True)
    row = Column(Integer, primary_key=True)
    username = Column(String(255), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id"))

# ===========================================================================
# CRAWLER
# ===========================================================================
class CrawlerPage(Base):
    __tablename__ = "pages"
    __table_args__ = {"schema": "crawler"}
    url_hash = Column(String(64), primary_key=True)
    url = Column(Text, nullable=False)
    gsp_cell = Column(String(10))
    title = Column(Text)
    content = Column(Text)
    out_links = Column(JSONB, default=[])
    pagerank = Column(Float, default=0.0)
    last_crawled = Column(DateTime, server_default="now()")

class OTP(Base):
    __tablename__ = "otps"
    __table_args__ = {"schema": "public"}
    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(20), nullable=False)
    code = Column(String(6), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default="now()")

#
==========================================================# ===========================================================================
# NEWS SUB..
# ===========================================================================
class NewsSubscription(Base):
    __tablename__ = "news_subscriptions"
    __table_args__ = {"schema": "social"}
    user_id = Column(UUID(as_uuid=True), ForeignKey("public.users.id", ondelete="CASCADE"), primary_key=True)
    category = Column(String(50), primary_key=True)
    subscribed_at = Column(DateTime, server_default="now()")