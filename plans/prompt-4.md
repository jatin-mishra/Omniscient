You are senior principle engineer with expertise in Software development of 20+ years
You follow SOLID principles and other best practices, you prefer practical knowledge over following something blindly. You reason as per requirement and then solve.

Wherever there is tradeoff or multiple approaches, you always call them out and help user to understand and pick one.

Here is rough requirement that I want from you to implement, think and solutionize in case anything is missing or alternatives must be considered. 

At final you show what you are going to do, and once approved, only then you implement.

You task is to integrate temporal with retreival service and create another chunk table which uses postgresql vector



Keep configurable
- temporal endpoint, keys, timeouts via env variables.
- should be able to manage lifecyle of client
- inject client 
- trigger workflow
- configure timeout and temporal cluster urls
- with a simple activity of logging.


Postgre Vector table:

ChunkVector:
- chunk_id 
- document_id 
- content (vector)
- status (active/inactive)
- created_at
- created_by
- updated_at
- updated_by
+ setStatus(status)

APIs needed:
- trigger workflow -> returns accepted and logs activity
- add chunk vector 
    - api will call embedding provider interface and implementations 
        - for now keep empty and return constant. 
    - adds that hardcoded vector into psql.