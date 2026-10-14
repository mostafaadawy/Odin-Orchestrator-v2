-- G8 rollback: removes ONLY the added column. Nothing else in the schema is touched.
ALTER TABLE public.files DROP COLUMN IF EXISTS created_by;
