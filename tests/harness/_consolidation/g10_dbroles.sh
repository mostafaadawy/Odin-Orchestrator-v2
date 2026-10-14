#!/bin/bash
PGHOST=/tmp/odc_pg PGPORT=25432 psql -d odin_core_con -Atc "select id||' | '||coalesce(role,'')||' | '||left(coalesce(description,''),40) from agents where id in ('devops','easypost','email','fullstack','qa','security') order by id"
