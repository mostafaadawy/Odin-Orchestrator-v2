select id,name,role,nature from agents where lower(name) in ('analytics','easypost','fullstack','devops','qa','email') order by lower(name);
select project_id, agent_id from project_agents where project_id like 'brand2%' or project_id like 'sandbox%' or project_id like 'backend-sandbox%' order by 1;
select owner_id,name,source_path,mode from dependencies order by 1;
