-- lua-scripts/main.lua


local mysql = require('resty.mysql')
local original_request_uri_args = ngx.req.get_uri_args()
local last_part = string.match(ngx.var.uri, "[^/]+$")


local mysql_query = "select distinct topic from partitions join files on partition_id=id where file_name=\"" .. last_part .."\";"

-- MySQL connection settings
local db, err = mysql:new()
if not db then
    ngx.status = 500
    ngx.say("Failed to initialize MySQL: ", err)
    return
end

db:set_timeout(1000) -- 1 sec

local ok, err, errno, sqlstate = db:connect{
    host = "10.5.0.6",
    port = 3306,
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
    ngx.say("/dManager".. raw["topic"]  .. ngx.var.uri)
    local subrequest_uri = "/dManager".. raw["topic"]  .. ngx.var.uri
   
    toCapture[i]=subrequest_uri
end

db:close()
ngx.say(toCapture)

local response={}

for i,raw in pairs(toCapture) do
    local err
    response[i], err = ngx.location.capture(toCapture[i])
    if err then
        ngx.status = 500
        ngx.say("Internal Server Error")
        return ngx.exit(ngx.status)
    end

end
if #toCapture==0 then
    ngx.status = 404

    ngx.say("file not found")
    
    ngx.eof()
end
local chunk_size=131072
local e=0
-- Concatenate chunks of responses into a single body
local condiction=true
while condiction  do

    local concatenated_body = ""
    for i,res in pairs(response) do

        local start_index = e
        local end_index = e + chunk_size - 1
        local tempString=string.sub(res.body, i, i + tonumber(chunk_size) - 1)
        concatenated_body = concatenated_body .. tempString
        ngx.say(concatenated_body)

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





