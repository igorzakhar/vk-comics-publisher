import argparse
import logging
import os
import random

from pathlib import Path

from urllib.parse import urlparse

import requests

from dotenv import load_dotenv


def download_random_comic(total_number):
    random.seed()
    num = random.randint(1, total_number)
    api_url = f'https://xkcd.com/{num}/info.0.json'

    response = requests.get(api_url)
    response.raise_for_status()

    comics_metadata = response.json()
    img_link = comics_metadata["img"]

    alt = comics_metadata.get("alt")

    response = requests.get(img_link)
    response.raise_for_status()

    url_path = urlparse(img_link).path
    comics_filename = Path(url_path).name
    with open(comics_filename, 'wb') as fp:
        fp.write(response.content)

    return comics_filename, alt


def _upload_comics(token, api_version, filename):
    api_endpoint = 'https://api.vk.com/method/photos.getWallUploadServer'
    params = {'access_token': token, 'v': api_version}
    response = requests.get(api_endpoint, params=params)
    response.raise_for_status()

    upload_url = response.json()['response']['upload_url']
    with open(filename, 'rb') as fp:
        files = {
            'photo': fp
        }
        upload_response = requests.post(upload_url, files=files)
        upload_response.raise_for_status()

    upload_metadata = upload_response.json()
    server = upload_metadata['server']
    photo = upload_metadata['photo']
    photo_hash = upload_metadata['hash']

    return server, photo, photo_hash


def _save_comics(token, api_ver, server, photo, photo_hash):
    api_endpoint = 'https://api.vk.com/method/photos.saveWallPhoto'
    params = {
        'access_token': token,
        'v': api_ver,
        'server': server,
        'photo': photo,
        'hash': photo_hash,
    }
    save_photo_response = requests.post(api_endpoint, params=params)
    save_photo_response.raise_for_status()

    saved_photo_metadata = save_photo_response.json()

    owner_id = saved_photo_metadata['response'][0]['owner_id']
    photo_id = saved_photo_metadata['response'][0]['id']

    return owner_id, photo_id


def _post_comics(token, api_ver, group_id, owner_id, photo_id, alt):
    api_endpoint = 'https://api.vk.com/method/wall.post'
    params = {
        'access_token': token,
        'v': api_ver,
        'owner_id': f'-{group_id}',
        'from_group': 1,
        'attachments': f'photo{owner_id}_{photo_id}',
        'message': alt,
    }
    response = requests.get(api_endpoint, params=params)
    response.raise_for_status()
    return response.json()


def post_comics_on_wall(group_id, token, api_v, filename, alt):

    server, img, img_hash = _upload_comics(token, api_v, filename)
    owner_id, img_id = _save_comics(token, api_v, server, img, img_hash)
    post_metadata = _post_comics(token, api_v, group_id, owner_id, img_id, alt)

    logging.debug(post_metadata)


def process_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true')
    return parser.parse_args()


def main():
    load_dotenv()

    args = process_args()

    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging_level = logging.INFO
    if args.debug:
        logging_level = logging.DEBUG

    logging.basicConfig(
        level=logging_level,
        format='%(funcName)s() \u2192  %(message)s'
    )

    vk_group_id = os.getenv('VK_GROUP_ID')
    vk_token = os.getenv('VK_ACCESS_TOKEN')
    vk_api_version = os.getenv('VK_VERSION_API')

    xkcd_response = requests.get('https://xkcd.com/info.0.json')
    xkcd_response.raise_for_status()
    comics_total_number = xkcd_response.json().get('num')

    comics_filename, alt = download_random_comic(comics_total_number)

    try:
        post_comics_on_wall(
            vk_group_id,
            vk_token,
            vk_api_version,
            comics_filename,
            alt
        )
    finally:
        file_to_remove = Path(comics_filename)
        file_to_remove.unlink()


if __name__ == '__main__':
    main()
