CREATE OR REPLACE VIEW agent_vw_com_categories AS
SELECT
    id,
    name,
    permalink
FROM tl_com_categories;