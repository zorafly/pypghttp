
#!/usr/bin/env python3

import sys, os, urllib, pickle, requests, json

class objview(object):
    def __init__(self, d):
        self.__dict__ = d

class apiclient_v4():
    def __init__(self, server, key):
        self.server = server
        self.key = key
        
    def request_post(self, endpoint, data):
        data["key"] = self.key
        response = requests.post("{}/v3/{}".format(self.server, endpoint),
                                data=data)
        if response.status_code == 200:
            return response.json()
        return None
    
    def request_get(self, endpoint, data):
        data["key"] = self.key
        response = requests.get("{}/v3/{}".format(self.server, endpoint),
                                params=data)        
        if response.status_code == 200:
            return response.json()
        return None
    
    def select(self, query):
        return self.request_get("select", {"query":query})

    def execute(self, query):
        return self.request_post("execute", {"query":query})


    
