You are senior principle engineer with expertise in Software development of 20+ years
You follow SOLID principles and other best practices, you prefer practical knowledge over following something blindly. You reason as per requirement and then solve.

Wherever there is tradeoff or multiple approaches, you always call them out and help user to understand and pick one.

Here is rough requirement that I want from you to implement, think and solutionize in case anything is missing or alternatives must be considered. 

At final you show what you are going to do, and once approved, only then you implement.

You will implement in retrieval now. 
- remove any existing api if present.

PostgreSql:

Directory:
- id 
- name 
- parent_id
- status (active / inactive)
- created_at
- updated_at
- updated_by
- created_by
+ setName(name)
+ setParentId(directoryId)
+ setStatus(status)


Document:
- id
- name
- document-type
- file-type
- content-type
- size_in_bytes

- directory_id
- chunking_strategy
- embedding_model

- provider : aws/gcp
- bucket
- storage_path
- raw_storage_url (s3 url / gcp object store)
- etag

- upload_status (INITIATED / IN_PROGRESS / SUCCESS / FAILED )
- status (active / inactive)

- version
- created_at
- created_by
- updated_at
- updated_by

+ setName(name)
+ setDirectory(directoru_id)
+ setEtag(etag)
+ setStorageUrl(url)
+ setUploadStatus(upload_status)
+ setStatus(status)


ElasticSearch:

Chunk:
- chunk_id 
- document_id 
- status (active/inactive)

- state (chunking, media_captioning, contextualizing, work_item_creation, embedding)
- StateStatus (in-progress, success, failure)

- content
- content_summary
- document_summary
- content_checksum

- metadata{}
- changes[]

- version
- created_at
- created_by
- updated_at
- updated_by
+ setStatus(status)


APIs needed:


1. create directory 
2. update directory
3. upload document
4. update document 
5. add chunk
6. update chunk 

updates only cover as per setters added.
