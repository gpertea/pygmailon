#!/usr/bin/env python
import os
import pickle
# Gmail API utils
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
# for encoding/decoding messages in base64
from base64 import urlsafe_b64decode, urlsafe_b64encode
# for dealing with attachement MIME types
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from mimetypes import guess_type as guess_mime_type

# Request all access (permission to read/send/receive emails, manage the inbox, and more)
SCOPES = ['https://mail.google.com/']
our_email = 'geo.pertea@gmail.com'

def gmail_authenticate():
    creds = None
    # the file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)
    # if there are no (valid) credentials availablle, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('oauth_cred_gmail.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)
    return build('gmail', 'v1', credentials=creds)

def get_last_email(service):
    results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=1).execute()
    messages = results.get('messages', [])
    if not messages:
        print('No new messages.')
    else:
        message = service.users().messages().get(userId='me', id=messages[0]['id']).execute()
        return message

def get_header(message, header_name):
    headers = message['payload']['headers']
    for header in headers:
        if header['name'] == header_name:
            return header['value']
    return None


def main():
    # get the Gmail API service
    service = gmail_authenticate()
    last_email = get_last_email(service)
    if last_email:
        sender = get_header(last_email, 'From')
        subject = get_header(last_email, 'Subject')
        print(f'Sender: {sender}')
        print(f'Subject: {subject}')

if __name__ == '__main__':
    main()