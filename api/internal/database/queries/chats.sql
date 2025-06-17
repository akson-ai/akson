-- name: CreateChat :one
INSERT INTO chats (id, title, assistant, created_at, updated_at)
VALUES ($1, $2, $3, NOW(), NOW())
RETURNING *;

-- name: GetChat :one
SELECT * FROM chats WHERE id = $1;

-- name: GetChats :many
SELECT * FROM chats ORDER BY updated_at DESC;

-- name: UpdateChat :one
UPDATE chats 
SET title = $2, assistant = $3, updated_at = NOW()
WHERE id = $1
RETURNING *;

-- name: UpdateChatAssistant :one
UPDATE chats 
SET assistant = $2, updated_at = NOW()
WHERE id = $1
RETURNING *;

-- name: DeleteChat :exec
DELETE FROM chats WHERE id = $1;

-- name: GetChatSummaries :many
SELECT id, 
       COALESCE(title, 'Untitled Chat') as title,
       updated_at as last_updated
FROM chats 
ORDER BY updated_at DESC;