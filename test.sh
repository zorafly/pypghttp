#!/usr/bin/env bash

query="select * from mt;"

response="$(curl -d '{"key": "dev", "action": "open"}' 127.0.0.1:8001/v4)"
echo $response
sid=`echo "$response" | jq -r '.content'`
echo "new session ID: $sid"

rpc=`cat <<EOF
{
	"key": "dev",
	"action": "verify",
	"sid": "$sid"
}
EOF
`
echo $rpc

curl -d "$rpc" 127.0.0.1:8001/v4

rpc=`cat <<"EOF"
{
	"key": "dev",
	"action": "select",
	"sid": "$sid",
	"query": "select * from mt"
}
EOF
`
echo $rpc

curl -d "$rpc" 127.0.0.1:8001/v4

rpc=`cat <<EOF
{
	"key": "dev",
	"action": "stream",
	"sid": "$sid",
	"query": "select * from mt"
}
EOF
`
echo $rpc

curl -d "$rpc" 127.0.0.1:8001/v4

rpc=`cat <<EOF
{
	"key": "dev",
	"action": "execute",
	"sid": "$sid",
	"query": "listen main"
}
EOF
`
echo $rpc

curl -d "$rpc" 127.0.0.1:8001/v4

rpc=`cat <<EOF
{
	"key": "dev",
	"action": "monitor",
	"sid": "$sid"
}
EOF
`
echo $rpc

curl -d "$rpc" 127.0.0.1:8001/v4

rpc=`cat <<EOF
{
	"key": "dev",
	"action": "close",
	"sid": "$sid"
}
EOF
`
echo $rpc

curl -d "$rpc" 127.0.0.1:8001/v4

