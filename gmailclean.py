#!/usr/bin/env python
import base64
import os.path
import email
from email.utils import getaddresses
import datetime
from google.oauth2.credentials import Credentials
#from google.oauth2 import credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

labelToMoveTo = '_Inbox_toDelete'
labelToMoveToId = None
specified_labels = ['__To_Follow_Up', '_LIBD_', '[imap]/sent', 'sent', 'useful', 'Personal', 'NotifyMe', 'Tennis', 'Work', 'Household']  # Replace with your label names
#specified_labels = ['[imap]/sent', 'Household']


def get_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('oauth_cred_gmail.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

## fn to extract email sender, recipient (or other header) from message
def getEmailElem(message, hdr):
        headers = message['payload']['headers']
        for header in headers:
            if header['name'] == hdr:
                #emails = [parseaddr(recipient)[1].lower() for recipient in header['value'].split(',')]
                emails = [email_address.lower() for display_name, email_address in getaddresses([header['value']])]
                return emails
        return None

def get_senders_to_keep(service, label_names):
    # Convert label_names to lowercase for case-insensitive comparison
    global labelToMoveToId
    lower_label_names = {name.lower() for name in label_names}
    # Fetch the list of labels once
    response = service.users().labels().list(userId='me').execute()
    label_names_kept = []
    sent_label_names_kept = []
    label_ids = []
    sent_label_ids = []
    for label in response.get('labels', []):
        if label['name'] == labelToMoveTo:
            labelToMoveToId = label['id']
            continue
        label_name_lower = label['name'].lower()
        if label_name_lower.endswith('sent'):
            sent_label_ids.append(label['id'])
            sent_label_names_kept.append(label_name_lower)
        else:
            if label_name_lower in lower_label_names:
                label_ids.append(label['id'])
                label_names_kept.append(label_name_lower)
            # also check if any of lower_label_names are the prefix of label_name_lower
            elif any(label_name_lower.startswith(name) for name in lower_label_names):
                label_ids.append(label['id'])
    senders_to_keep = set()

    # Process messages in specified labels to get senders
    for label in label_ids:
        page_token = None
        while True:
            response = service.users().messages().list(userId='me', labelIds=[label], pageToken=page_token).execute()
            if 'messages' in response:
                for message_info in response['messages']:
                    message = service.users().messages().get(userId='me', id=message_info['id']).execute()
                    sender = getEmailElem(message, 'From')[0]
                    if sender:
                        senders_to_keep.add(sender)
            page_token = response.get('nextPageToken')
            if not page_token:
                break

    # Process messages in Sent folders to get recipients
    for label in sent_label_ids:
        page_token = None
        while True:
            response = service.users().messages().list(userId='me', labelIds=[label], pageToken=page_token).execute()
            if 'messages' in response:
                for message_info in response['messages']:
                    message = service.users().messages().get(userId='me', id=message_info['id']).execute()
                    recipients = getEmailElem(message, 'To')
                    # if recipients array is not empty, add all recipients to senders_to_keep
                    if recipients and len(recipients) > 0:
                        senders_to_keep.update(recipients)
            page_token = response.get('nextPageToken')
            if not page_token:
                break

    return senders_to_keep

def list_messages(service, query):
    response = service.users().messages().list(userId='me', q=query).execute()
    messages = []
    if 'messages' in response:
        messages.extend(response['messages'])
    while 'nextPageToken' in response:
        page_token = response['nextPageToken']
        response = service.users().messages().list(userId='me', q=query, pageToken=page_token).execute()
        messages.extend(response['messages'])
    return messages

def main():
    service = get_service()
    senders_to_keep = get_senders_to_keep(service, specified_labels)
    # Get the label id for "Inbox_toDelete"
    label_id =labelToMoveToId
    if label_id is None:
        print(f'Label "Inbox_toDelete" not found. Please create the label and run the script again.')
        return
    
    # Print the number of entries in senders_to_keep
    print(f'Number of senders to keep: {len(senders_to_keep)}')
    # The following lines are to be added:
    with open('senders_keep.txt', 'w') as file:
        for sender in senders_to_keep:
            file.write(f'{sender}\n')
    
    #three_months_ago = (datetime.datetime.now() - datetime.timedelta(days=90)).isoformat()
    three_months_ago = (datetime.datetime.now() - datetime.timedelta(days=90)).strftime('%Y/%m/%d')
    messages = list_messages(service, f'before:{three_months_ago} in:inbox')
    # Print the total number of messages selected by the filter
    print(f'Total number of messages to process: {len(messages)}')
    if len(messages) > 0:        
        processed_counter = 0  # Counter for number of messages processed
        for message_info in messages:
            message = service.users().messages().get(userId='me', id=message_info['id']).execute()
            sender = getEmailElem(message, 'From')[0]
            if sender not in senders_to_keep:
                #service.users().messages().delete(userId='me', id=message_info['id']).execute()
                # Remove the 'INBOX' label and add the 'Inbox_toDelete' label
                modify_request = {
                    'removeLabelIds': ['INBOX'],
                    'addLabelIds': [label_id]
                }
                service.users().messages().modify(userId='me', id=message_info['id'], body=modify_request).execute()
            # Increment the processed counter and print every 5000 messages
            processed_counter += 1
            if processed_counter % 5000 == 0:
                print(f'Processed {processed_counter} messages so far')

if __name__ == '__main__':
    main()
