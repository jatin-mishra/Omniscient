# Functional Requirements
- CRUD user, manager, team, groups
    - team level
        - approvers 
        - ticket system integration
        - notification integration
- Add RCAs document [ md file > docx ]
    - Impact
    - Background (System Overview)
    - Trigger (Cause)
    - Detection
    - Root cause
    - Lesson learned
    - 5 why analysis
    - Mitigations & Action items 
    - Complete Timeline 
    - Summary
- update RCA document 
- Get Approval 
- ask query 
- create tickets
- ticket webhooks
- track action items 
- alert on timeline using pager duty
- teams / slack alias to directly ask question
    - @omniscient add <document>
    - @omniscient approve: if any approvers write approved then it approves it 
    - @omniscient query <>
    - @omniscient action-items status  
    - ....


# Non Functional
Non Functional 
- users total - 5k 
- users per team, max 30
- indexing within an hour 
- query < 5s 