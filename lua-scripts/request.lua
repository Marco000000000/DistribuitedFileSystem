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
    
    local subrequest_uri = "/dManager".. raw["topic"]  .. ngx.var.uri
   
    toCapture[i]=subrequest_uri
end
db:close()

if #toCapture==0 then
    ngx.status = 404

    ngx.say("file not found")
    
    ngx.eof()
end



local response={}

for i,raw in ipairs(toCapture) do
    
    local res, err = ngx.location.capture(toCapture[i])
    if err then
        ngx.status = 500
        ngx.say("Internal Server Error")
        return ngx.exit(ngx.status)
    end
    table.insert(response, res.body)
end


local chunk_size=131072
local maxLen=0
local str=""

for _, res in ipairs(response) do
    maxLen = math.max(maxLen, #res)
    ngx.say(#res)

end
-- Interleave bytes every specified interval

for i = 1, maxLen, chunk_size do
    for _,str in ipairs(response) do
        if str ~= nil then
            local slice = str:sub(i, i + chunk_size - 1) or ""
            ngx.say(slice)
        end
        
    end
end

ngx.eof()





