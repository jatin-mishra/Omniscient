You are senior principle engineer with expertise in Software development of 20+ years
You follow SOLID principles and other best practices, you prefer practical knowledge over following something blindly. You reason as per requirement and then solve.

Wherever there is tradeoff or multiple approaches, you always call them out and help user to understand and pick one.

Here is rough requirement that I want from you to implement, think and solutionize in case anything is missing or alternatives must be considered. 

At final you show what you are going to do, and once approved, only then you implement.


Context:
We have separate directories  and all code related into it. 
like this 
1. onboarding 
2. policy_engine 
3. retrieval 
4. audit 
5. tracker 


root level:
1. main
2. middlewares 
3. errors
4. global router

any thing common around all.

I am building like this so in future if needed we can extract onboarding,policy engine etc to different microservice.


Task:

Your task is to implement policy engine.

Postgresql:
permission enum in code:
- team:create
- team:add_user
- team:update
- team:delete

- panel:create
- panel:add_user
- panel:update
- panel:delete

- user:create 
- user:update 
- user:delete 

- directory:create 
- directory:read 
- directory:upload
- directory:approve 

- document:read
- document:approve 
- document:delete

Here are models:

Permission: 
- external_id as pk
- name (enum in code / string in db)
- status - active/inactive
- createdAt
- createdBy
+ setStatus(status)

Policy:
- external_id as pk
- permissionId
- effect (Enum - ALLOW/DENY)
- status - active/inactive 
- createdAt
- createdBy
- updatedAt
- updatedBy 
+ setStatus(status)

UserPermission:
- external_id as pk
- entity_type (team / group / user)
- entity_id
- policy_id 
- resource_type
- resource_id 
- status (active/inactive)
- created_at
- created_by
- updated_at
- updated_by
+ markStatus(status)


possible resource ids as per permission
(
    - team:create -> "ALL"
    - team:add_user -> "ALL"
    - team:update -> "ALL" / id 
    - team:delete -> "ALL" / id

    - panel:create -> "ALL"
    - panel:add_user -> "ALL"
    - panel:update -> "ALL" / id 
    - panel:delete -> "ALL" / id 

    - user:create -> "ALL"
    - user:update -> "ALL" 
    - user:delete -> "ALL" 


    - directory:create -> "ALL" / team_id 
    - directory:read -> "ALL" / team_id / directory_id
    - directory:upload -> "ALL" / team_id / directory_id
    - directory:approve -> "ALL" / team_id / directory_id


    - document:read -> "ALL" / team_id / directory_id / document_id
    - document:approve -> "ALL" / team_id / directory_id / document_id
    - document:delete -> "ALL" / team_id / directory_id / document_id
)

and resource type will be added accordingly.
If resource_id is directory_id then resource_type is directory.
If resource_id is team_id then resource_type is team.
If resource_id is document_id then resource_type is document.
... etc.


APIs needed:
- add permission
- update permission -> allow status only

- add policy 
- update policy -> allow status only 

- add user permission
- update user permission -> allow status only

