# Database design

Initial relational entities are `users`, `birth_profiles`, and `birth_charts`, with UUID primary keys and UTC creation timestamps. Profile ownership is enforced in query predicates and foreign keys cascade profile deletion to its charts. The requested full normalized schema, Alembic revision history, field-level encryption and refresh-token/session tables remain pending. Birth data should be treated as sensitive and production deployments must add encryption/key management before launch.
