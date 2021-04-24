import ujson as json
from pathlib import Path
from configparser import ConfigParser
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.nlp.v20190408 import nlp_client, models
try:
    from src.common.log import logger
except ImportError:
    from loguru import logger


cfg = ConfigParser()
cfg.read(Path(__file__).parent/"tccli_config.ini")
APP_ID = dict(cfg.items('key'))['app_id']
APP_KEY = dict(cfg.items('key'))['app_key']


try: 
    cred = credential.Credential(APP_ID, APP_KEY) 
    httpProfile = HttpProfile()
    httpProfile.endpoint = "nlp.tencentcloudapi.com"

    clientProfile = ClientProfile()
    clientProfile.httpProfile = httpProfile
    client = nlp_client.NlpClient(cred, "ap-guangzhou", clientProfile) 

    req = models.ChatBotRequest()
except TencentCloudSDKException as err: 
    logger.error(err)


def ai_chat(query):
    try:
        params = {
            "Query": query
        }
        req.from_json_string(json.dumps(params))
        resp = client.ChatBot(req)
        return resp.Reply, resp.Confidence

    except TencentCloudSDKException as err: 
        logger.error(err)

    
if __name__ == "__main__":
    print(APP_ID, APP_KEY)
    while True:
        query = input()
        if query == 'cancel':
            break
        else:
            reply, confidence = ai_chat(query)
            print(f'reply: {reply}\nconfidence: {confidence}')