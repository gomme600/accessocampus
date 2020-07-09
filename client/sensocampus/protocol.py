MQTT_COMMAND_SCHEMA = {"type": "object", "properties": {"dest": {"type": "string"}, "order": {"type": "string"}}}

SENSO_CREDENTIALS_SCHEMA =\
{
    "type": "object",
    "properties":
    {
        "login": { "type": "string" },
        "password": {"type": "string", "required": False },
        "server": {"type": "string", "required": False },
        "port": {"type": "integer", "required": False }
    }
}

SENSO_CONFIG_SCHEMA =\
{
    "type": "object",
    "properties":
    {
        "topics":
        {
            "type": "array",
            "items": {"type": "string"}
        },

        "zones":
        {
            "type": "array",
            "items":
            {
                "type": "object",
                "properties":
                {
                    "modules":
                    {
                        "type": "array",
                        "items":
                        {
                            "type": "object",
                            "properties":
                            {
                                "module": {"type": "string"},
                                "unit": {"type": "string"},
                                "params":
                                {
                                    "type": "array",
                                    "items":
                                    {
                                        "type": "object",
                                        "properties":
                                        {
                                            "param": {"type": "string"},
                                            "value": {"type": "any"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
