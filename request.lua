-- lua-scripts/main.lua


local mysql = require("resty.mysql")
local cjson = require("cjson")
local original_request_uri_args = ngx.req.get_uri_args()

local mysql_query = "select distinct topic from partitions join file on partition_id=id where file_name=" .. original_request_uri_args

-- MySQL connection settings
local db, err = mysql:new()
if not db then
    ngx.status = 500
    ngx.say("Failed to initialize MySQL: ", err)
    return
end

db:set_timeout(1000) -- 1 sec

local ok, err, errno, sqlstate = db:connect{
    host = "localhost",
    port = 3307,
    database = "ds_filesystem",
    user = "root",
    password = "giovanni",
}

if not ok then
    ngx.status = 500
    ngx.say("Failed to connect to MySQL: ", err)
    return
end

local res, err, errno, sqlstate = db:query(mysql_query)
if not res then
    ngx.status = 500
    ngx.say("Failed to query MySQL: ", err)
    return
end

local len=#res
local toCapture={}

for i, raw in pairs(res) do

    local subrequest_uri = "dManager".. raw["topic"] .. ngx.var.uri
    local subrequest_args = ngx.encode_args(original_request_uri_args)
    if subrequest_args ~= "" then
        subrequest_uri = subrequest_uri .. "?" .. subrequest_args
    end
    
    toCapture[i]=subrequest_uri
end

db:close()

local response={}

for i,raw in pairs(toCapture) do

    local response[i], err = ngx.location.capture(subrequest_uri)
    if err then
        ngx.status = 500
        ngx.say("Internal Server Error")
        return ngx.exit(ngx.status)
    end

end

ngx.status = 200
local e=0
-- Concatenate chunks of responses into a single body
local condiction=true
while condiction then

    local concatenated_body = ""
    for i,res in pairs(response) do

        local start_index = e
        local end_index = e + chunk_size - 1
        local tempString=string.sub(res.body, i, i + tonumber(ngx.var.chunk_size) - 1)
        concatenated_body = concatenated_body .. tempString
        if string.len(tempString)<chunk_size then
            condiction=false

            break
        end
    -- Check if this is the last chunk
        if end_index >= length then
            break
        end

        e = end_index + 1
    end
    ngx.say(concatenated_body)
end
ngx.eof()


