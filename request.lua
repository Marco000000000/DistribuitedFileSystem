-- lua-scripts/main.lua
local original_request_uri_args = ngx.req.get_uri_args()

-- Construct the subrequest URI with the same parameters
local subrequest_uri = "/backend" .. ngx.var.uri
local subrequest_args = ngx.encode_args(original_request_uri_args)
if subrequest_args ~= "" then
    subrequest_uri = subrequest_uri .. "?" .. subrequest_args
end

-- Make the subrequest
local response, err = ngx.location.capture(subrequest_uri)
local response1, err1 = ngx.location.capture("/dManager1")
local response2, err2 = ngx.location.capture("/dManager2")

if err1 or err2 then
    ngx.status = 500
    ngx.say("Internal Server Error")
    return ngx.exit(ngx.status)
end

-- Concatenate chunks of responses into a single body
local concatenated_body = ""
--while i <= length do
--    local start_index = i
--    local end_index = i + chunk_size - 1
--    local chunk = string.sub(body, start_index, end_index)
--    table.insert(chunks, chunk)
--
--    -- Check if this is the last chunk
--    if end_index >= length then
--        break
--    end
--
--    i = end_index + 1
--end
for _, res in ipairs(responses) do
    if res.body then
        -- Read chunks of the specified size
        for i = 1, #res.body, tonumber(ngx.var.chunk_size) do
            concatenated_body = concatenated_body .. string.sub(res.body, i, i + tonumber(ngx.var.chunk_size) - 1)
        end
    end-- Method 1: Using string.len

end

ngx.status = 200
ngx.say(concatenated_body)
ngx.eof()
