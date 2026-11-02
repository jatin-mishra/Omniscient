You are senior principle engineer with expertise in Software development of 20+ years
You follow SOLID principles and other best practices, you prefer practical knowledge over following something blindly. You reason as per requirement and then solve.

Wherever there is tradeoff or multiple approaches, you always call them out and help user to understand and pick one.

Here is rough requirement that I want from you to implement, think and solutionize in case anything is missing or alternatives must be considered. 

At final you show what you are going to do, and once approved, only then you implement.

LLD:

Given definitions are models, for which we need CRUD.
- add/post 
- update/patch
- get

default, id: Long, externalId: (UUID)

Team:
- id 
- external_id
- name 
- manager 
- status (Active/Inactive)
+ setName(string)
+ setManager(string)
+ setStatus(status)

User:
- id 
- external_id
- name
- team_id
- status (active / inactive)
+ setTeam(string)
+ setStatus(status)
+ setName(string)

Group:
- id 
- external_id 
- name
- status (active / inactive)
+ setName(string)
+ setStatus(status)

GroupUser:
- id 
- external_id 
- group_id 
- user_id 
- status (active / inactive )
+ setStatus(status)

Create a separate directory - called onboarding, and all code related to this into it. 
App will have multiple directories like this 
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