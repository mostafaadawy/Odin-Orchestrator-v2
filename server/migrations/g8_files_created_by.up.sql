-- G8 (owner decision 2026-10-11, option A): record which agent created a file.
-- ADD ONLY: one nullable column, no default, no constraint, no index. Existing rows stay untouched (NULL = "unknown").
-- Views (v_capability, v_chat, ...) list their columns explicitly, so they do not change.
ALTER TABLE public.files ADD COLUMN IF NOT EXISTS created_by text;
COMMENT ON COLUMN public.files.created_by IS 'G8: creating agent as JSON {agent, project, via, ts}; NULL = unknown';
