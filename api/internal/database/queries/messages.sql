-- name: CreateMessage :one
INSERT INTO messages (id, chat_id, role, name, content, tool_call_id, tool_call_name, tool_call_arguments, created_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
RETURNING *;

-- name: GetMessage :one
SELECT * FROM messages WHERE id = $1;

-- name: GetMessagesByChatID :many
SELECT * FROM messages 
WHERE chat_id = $1 
ORDER BY created_at ASC;

-- name: UpdateMessage :one
UPDATE messages 
SET content = $2
WHERE id = $1
RETURNING *;

-- name: DeleteMessage :exec
DELETE FROM messages WHERE id = $1;

-- name: DeleteMessagesByChatID :exec
DELETE FROM messages WHERE chat_id = $1;

-- name: GetMessageCount :one
SELECT COUNT(*) FROM messages WHERE chat_id = $1;