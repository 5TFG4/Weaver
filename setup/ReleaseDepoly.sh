docker build -f dockerfile_release -t weaver_release .
docker run -d --name weaver_release -v ~/Projects/Weaver:/workspaces/weaver weaver_release tail -f /dev/null
