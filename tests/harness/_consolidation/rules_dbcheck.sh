#!/bin/bash
# read-only: does odin_core (copy clone, 25432) store rules or file content anywhere?
export PGHOST=/tmp/odc_pg PGPORT=25432
psql -d odin_core_con -Atc "select table_name||'.'||column_name from information_schema.columns where table_schema='public' and (column_name ilike '%rule%' or table_name ilike '%rule%' or column_name ilike '%content%' or column_name ilike '%skill%')"
psql -d odin_core_con -Atc "select string_agg(column_name, ',') from information_schema.columns where table_name='files'"
psql -d odin_core_con -Atc "select string_agg(column_name, ',') from information_schema.columns where table_name='agents'"
