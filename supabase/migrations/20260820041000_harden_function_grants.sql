-- Revoke public execute on SECURITY DEFINER helper; fix search_path on trigger fn.
REVOKE EXECUTE ON FUNCTION public.rls_auto_enable() FROM PUBLIC, anon, authenticated;
ALTER FUNCTION public.set_updated_at() SET search_path = public;
