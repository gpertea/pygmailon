#!/usr/bin/env python
import base64
import email
import datetime
from google.oauth2 import credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_service():
    creds = None
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file('oauth_cred_gmail.json', SCOPES)
        creds = flow.run_local_server(port=0)
    return build('gmail', 'v1', credentials=creds)

def get_sender_from_message(message):
    headers = message['payload']['headers']
    for header in headers:
        if header['name'] == 'From':
            return header['value']
    return None

def get_label_id(service, label_name):
    response = service.users().labels().list(userId='me').execute()
    for label in response.get('labels', []):
        if label['name'] == label_name:
            return label['id']
    return None

def get_senders_to_keep(service, label_names):
    # Convert label_names to lowercase for case-insensitive comparison
    lower_label_names = {name.lower() for name in label_names}
    # Fetch the list of labels once
    response = service.users().labels().list(userId='me').execute()
    label_ids = []
    for label in response.get('labels', []):
        if label['name'].lower() in lower_label_names:
            label_ids.append(label['id'])

    senders_to_keep = set()
    for label_id in label_ids:
        response = service.users().messages().list(userId='me', labelIds=[label_id]).execute()
        if 'messages' in response:
            for message_info in response['messages']:
                message = service.users().messages().get(userId='me', id=message_info['id']).execute()
                sender = get_sender_from_message(message)
                if sender:
                    senders_to_keep.add(sender)

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
    specified_labels = ['__To_Follow_Up', '_LIBD_', '[imap]-sent', 'sent', 'Personal', 'NotifyMe', 'Tennis', 'Work', 'Household']  # Replace with your label names
    service = get_service()
    # Get the label id for "Inbox_toDelete"
    label_id = get_label_id(service, "Inbox_toDelete")
    if label_id is None:
        print(f'Label "Inbox_toDelete" not found. Please create the label and run the script again.')
        return
    
    senders_to_keep = get_senders_to_keep(service, specified_labels)
    # Print the number of entries in senders_to_keep
    print(f'Number of senders to keep: {len(senders_to_keep)}')
    # Optionally print the list of emails in senders_to_keep
    print_senders_list = False  # Set to True if you want to print the list
    if print_senders_list:
        print(f'List of senders to keep: {", ".join(senders_to_keep)}')

    #three_months_ago = (datetime.datetime.now() - datetime.timedelta(days=90)).isoformat()
    three_months_ago = (datetime.datetime.now() - datetime.timedelta(days=90)).strftime('%Y/%m/%d')
    messages = list_messages(service, f'before:{three_months_ago} in:inbox')
    # Print the total number of messages selected by the filter
    print(f'Total number of messages to process: {len(messages)}')
    #response = service.users().messages().list(userId='me', q=f'before:{three_months_ago} in:inbox').execute()
    ## Print the estimated total number of messages selected by the filter
    #print(f'Estimated total number of messages to process: {response.get("resultSizeEstimate", 0)}')
    if len(messages) > 0:        
        processed_counter = 0  # Counter for number of messages processed
        for message_info in messages:
            message = service.users().messages().get(userId='me', id=message_info['id']).execute()
            sender = get_sender_from_message(message)
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
