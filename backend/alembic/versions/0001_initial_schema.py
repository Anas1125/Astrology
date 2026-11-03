"""Initial AstroAI relational schema."""
from alembic import op
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, JSON, Numeric, String, Text, Time, UniqueConstraint, Uuid

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("users", Column("id", Uuid(), primary_key=True), Column("email", String(320), nullable=False), Column("password_hash", String(255), nullable=False), Column("role", String(32), nullable=False), Column("is_active", Boolean(), nullable=False), Column("preferred_language", String(5), nullable=False), Column("created_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table("subscription_plans", Column("id", Uuid(), primary_key=True), Column("code", String(32), nullable=False), Column("name", String(80), nullable=False), Column("active", Boolean(), nullable=False), Column("created_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_subscription_plans_code", "subscription_plans", ["code"], unique=True)
    op.create_table("birth_profiles", Column("id", Uuid(), primary_key=True), Column("owner_id", Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False), Column("display_name", String(120), nullable=False), Column("relationship", String(32), nullable=False), Column("birth_date", Date(), nullable=False), Column("birth_time", Time(), nullable=True), Column("time_accuracy", String(20), nullable=False), Column("birthplace", String(200), nullable=False), Column("country", String(100), nullable=False), Column("latitude", Float(), nullable=True), Column("longitude", Float(), nullable=True), Column("timezone", String(80), nullable=True), Column("created_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_birth_profiles_owner_id", "birth_profiles", ["owner_id"])
    op.create_table("profile_permissions", Column("id", Uuid(), primary_key=True), Column("profile_id", Uuid(), ForeignKey("birth_profiles.id", ondelete="CASCADE"), nullable=False), Column("user_id", Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False), Column("permission", String(16), nullable=False), Column("created_at", DateTime(timezone=True), nullable=False), UniqueConstraint("profile_id", "user_id", name="uq_profile_permission_user"))
    op.create_index("ix_profile_permissions_profile_id", "profile_permissions", ["profile_id"])
    op.create_index("ix_profile_permissions_user_id", "profile_permissions", ["user_id"])
    op.create_table("birth_charts", Column("id", Uuid(), primary_key=True), Column("profile_id", Uuid(), ForeignKey("birth_profiles.id", ondelete="CASCADE"), nullable=False), Column("system", String(16), nullable=False), Column("division", String(16), nullable=False), Column("status", String(32), nullable=False), Column("unavailable_reason", Text(), nullable=False), Column("config", JSON(), nullable=False), Column("engine_version", String(80)), Column("ephemeris_version", String(80)), Column("created_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_birth_charts_profile_id", "birth_charts", ["profile_id"])
    op.create_table("chart_calculation_runs", Column("id", Uuid(), primary_key=True), Column("chart_id", Uuid(), ForeignKey("birth_charts.id", ondelete="CASCADE"), nullable=False), Column("run_number", Integer(), nullable=False), Column("status", String(24), nullable=False), Column("config", JSON(), nullable=False), Column("result", JSON()), Column("engine_version", String(80)), Column("ephemeris_version", String(80)), Column("timezone_assumption", String(120)), Column("error_code", String(80)), Column("created_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_chart_calculation_runs_chart_id", "chart_calculation_runs", ["chart_id"])
    op.create_index("ix_chart_runs_chart_created", "chart_calculation_runs", ["chart_id", "created_at"])
    op.create_table("chat_sessions", Column("user_id", Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False), Column("profile_id", Uuid(), ForeignKey("birth_profiles.id", ondelete="SET NULL")), Column("id", Uuid(), primary_key=True), Column("title", String(160), nullable=False), Column("language", String(5), nullable=False), Column("astrology_system", String(16), nullable=False), Column("created_at", DateTime(timezone=True), nullable=False), Column("updated_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
    op.create_index("ix_chat_sessions_profile_id", "chat_sessions", ["profile_id"])
    op.create_table("chat_messages", Column("session_id", Uuid(), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False), Column("id", Uuid(), primary_key=True), Column("role", String(16), nullable=False), Column("content", Text(), nullable=False), Column("provider", String(80)), Column("model", String(120)), Column("prompt_version", String(80)), Column("input_tokens", Integer(), nullable=False), Column("output_tokens", Integer(), nullable=False), Column("created_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_table("ai_usage_logs", Column("id", Uuid(), primary_key=True), Column("user_id", Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False), Column("message_id", Uuid(), ForeignKey("chat_messages.id", ondelete="SET NULL")), Column("feature", String(64), nullable=False), Column("period_key", String(16), nullable=False), Column("input_tokens", Integer(), nullable=False), Column("output_tokens", Integer(), nullable=False), Column("cost", Numeric(12, 6), nullable=False), Column("created_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_ai_usage_logs_user_id", "ai_usage_logs", ["user_id"])
    op.create_index("ix_ai_usage_user_feature_time", "ai_usage_logs", ["user_id", "feature", "created_at"])
    op.create_table("ai_prompt_versions", Column("id", Uuid(), primary_key=True), Column("name", String(100), nullable=False), Column("version", Integer(), nullable=False), Column("language", String(5), nullable=False), Column("astrology_system", String(16), nullable=False), Column("content", Text(), nullable=False), Column("active", Boolean(), nullable=False), Column("created_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_ai_prompt_versions_name", "ai_prompt_versions", ["name"])
    op.create_table("plan_entitlements", Column("id", Uuid(), primary_key=True), Column("plan_id", Uuid(), ForeignKey("subscription_plans.id", ondelete="CASCADE"), nullable=False), Column("feature", String(64), nullable=False), Column("limit_value", Integer()), Column("config", JSON(), nullable=False), UniqueConstraint("plan_id", "feature", name="uq_entitlement_plan_feature"))
    op.create_index("ix_plan_entitlements_plan_id", "plan_entitlements", ["plan_id"])
    op.create_table("user_subscriptions", Column("id", Uuid(), primary_key=True), Column("user_id", Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False), Column("plan_id", Uuid(), ForeignKey("subscription_plans.id"), nullable=False), Column("status", String(24), nullable=False), Column("period_start", DateTime(timezone=True), nullable=False), Column("period_end", DateTime(timezone=True), nullable=False), Column("cancel_at_period_end", Boolean(), nullable=False), Column("provider", String(32)), Column("provider_subscription_id", String(160)), Column("created_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_user_subscriptions_user_id", "user_subscriptions", ["user_id"])
    op.create_index("ix_user_subscriptions_plan_id", "user_subscriptions", ["plan_id"])
    op.create_index("ix_user_subscriptions_status", "user_subscriptions", ["status"])
    op.create_index("ix_user_subscriptions_provider_subscription_id", "user_subscriptions", ["provider_subscription_id"])
    op.create_table("payments", Column("id", Uuid(), primary_key=True), Column("user_id", Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False), Column("subscription_id", Uuid(), ForeignKey("user_subscriptions.id", ondelete="SET NULL")), Column("provider", String(32), nullable=False), Column("provider_payment_id", String(160)), Column("amount", Numeric(12, 2), nullable=False), Column("currency", String(3), nullable=False), Column("status", String(24), nullable=False), Column("created_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_payments_user_id", "payments", ["user_id"])
    op.create_index("ix_payments_subscription_id", "payments", ["subscription_id"])
    op.create_index("ix_payments_provider_payment_id", "payments", ["provider_payment_id"])
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_table("payment_webhooks", Column("id", Uuid(), primary_key=True), Column("provider", String(32), nullable=False), Column("event_id", String(160), nullable=False), Column("event_type", String(100), nullable=False), Column("payload", JSON(), nullable=False), Column("processed_at", DateTime(timezone=True)), Column("created_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_payment_webhooks_event_id", "payment_webhooks", ["event_id"], unique=True)
    op.create_table("reports", Column("id", Uuid(), primary_key=True), Column("user_id", Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False), Column("profile_id", Uuid(), ForeignKey("birth_profiles.id", ondelete="SET NULL")), Column("report_type", String(48), nullable=False), Column("status", String(24), nullable=False), Column("storage_key", String(512)), Column("language", String(5), nullable=False), Column("created_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_reports_user_id", "reports", ["user_id"])
    op.create_index("ix_reports_profile_id", "reports", ["profile_id"])
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_table("compatibility_reports", Column("id", Uuid(), primary_key=True), Column("user_id", Uuid(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False), Column("profile_a_id", Uuid(), ForeignKey("birth_profiles.id", ondelete="CASCADE"), nullable=False), Column("profile_b_id", Uuid(), ForeignKey("birth_profiles.id", ondelete="CASCADE"), nullable=False), Column("system", String(16), nullable=False), Column("status", String(24), nullable=False), Column("result", JSON()), Column("created_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_compatibility_reports_user_id", "compatibility_reports", ["user_id"])
    op.create_index("ix_compatibility_reports_profile_a_id", "compatibility_reports", ["profile_a_id"])
    op.create_index("ix_compatibility_reports_profile_b_id", "compatibility_reports", ["profile_b_id"])
    op.create_table("horoscope_contents", Column("id", Uuid(), primary_key=True), Column("period", String(12), nullable=False), Column("sign", String(32), nullable=False), Column("language", String(5), nullable=False), Column("starts_on", Date(), nullable=False), Column("ends_on", Date(), nullable=False), Column("content", Text(), nullable=False), Column("approved", Boolean(), nullable=False), UniqueConstraint("period", "sign", "language", "starts_on", name="uq_horoscope_period_sign_lang_date"))
    op.create_index("ix_horoscope_contents_sign", "horoscope_contents", ["sign"])
    op.create_table("panchang_entries", Column("id", Uuid(), primary_key=True), Column("local_date", Date(), nullable=False), Column("latitude", Float(), nullable=False), Column("longitude", Float(), nullable=False), Column("timezone", String(80), nullable=False), Column("status", String(24), nullable=False), Column("calculation", JSON()), Column("engine_version", String(80)), UniqueConstraint("local_date", "latitude", "longitude", name="uq_panchang_date_location"))
    op.create_index("ix_panchang_entries_local_date", "panchang_entries", ["local_date"])
    op.create_table("audit_logs", Column("id", Uuid(), primary_key=True), Column("actor_user_id", Uuid(), ForeignKey("users.id", ondelete="SET NULL")), Column("action", String(100), nullable=False), Column("resource_type", String(80), nullable=False), Column("resource_id", String(80)), Column("details", JSON(), nullable=False), Column("created_at", DateTime(timezone=True), nullable=False))
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_actor_created", "audit_logs", ["actor_user_id", "created_at"])


def downgrade():
    for table in ["audit_logs", "panchang_entries", "horoscope_contents", "compatibility_reports", "reports", "payment_webhooks", "payments", "user_subscriptions", "plan_entitlements", "ai_prompt_versions", "ai_usage_logs", "chat_messages", "chat_sessions", "chart_calculation_runs", "birth_charts", "profile_permissions", "birth_profiles", "subscription_plans", "users"]:
        op.drop_table(table)
