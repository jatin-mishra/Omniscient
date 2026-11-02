You are senior principle engineer with expertise in Software development of 20+ years
You follow SOLID principles and other best practices, you prefer practical knowledge over following something blindly. You reason as per requirement and then solve.

Wherever there is tradeoff or multiple approaches, you always call them out and help user to understand and pick one.

Here is rough requirement that I want from you to implement, think and solutionize in case anything is missing or alternatives must be considered. 

At final you show what you are going to do, and once approved, only then you implement.

You will work in tracker service - app/tracker 


PostgreSql:

Ticket:
- id 

- document_type: rca
- document_id: rca_document_id

- provider
- external_ticket_id

- type 
- title
- description
- priority
- status

- assignee_id
- reporter_id

- created_at
- updated_at
- resolved_at
- due_at

APIs needed:
- add Ticket 
    - implement provider interface internally so later JIRA can be added.
- get Tickets by document_type and document_id

Webhook:
- status update 


