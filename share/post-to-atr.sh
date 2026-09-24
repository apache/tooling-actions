#!/usr/bin/env bash
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

# POST the JSON on stdin to an ATR API URL, reporting any error from ATR as a workflow error annotation
# Usage: post-to-atr.sh URL DESCRIPTION
set -euo pipefail

url="$1"
description="$2"
response="$(mktemp)"
trap 'rm -f "$response"' EXIT

status="$(curl -sS -X POST -H 'Content-Type: application/json' -d @- -o "$response" -w '%{http_code}' "$url")"
if [[ "$status" == 2?? ]]
then
  cat "$response"
  echo
  exit 0
fi

message="$(jq -r '.error // empty' "$response" 2> /dev/null || true)"
request_id="$(jq -r '.request_id // empty' "$response" 2> /dev/null || true)"
if [[ -z "$message" ]]
then
  message="$(head -c 1000 "$response")"
fi
if [[ -n "$request_id" ]]
then
  message="$message (request ID $request_id)"
fi
# Escape the message so that ATR's text can't end the annotation and start another workflow command
message="${message//'%'/%25}"
message="${message//$'\r'/%0D}"
message="${message//$'\n'/%0A}"
echo "::error title=ATR could not ${description} (HTTP ${status})::${message}"
exit 1
