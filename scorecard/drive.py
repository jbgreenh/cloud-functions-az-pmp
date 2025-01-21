import polars as pl
import io
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload


def lazyframe_from_file_name_csv(service, file_name:str, folder_id:str, sep:str=',') -> pl.LazyFrame | None:
    '''
    return a lazyframe of the csv in the provided folder
    '''
    try:
        results = service.files().list(q=f"name = '{file_name}' and '{folder_id}' in parents",
                                    supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        files = results.get('files', [])
        file_id = None
        if files:
            file_id = files[0]['id']
            try:
                request = service.files().get_media(fileId=file_id)
            except HttpError as error:
                print(f'error checking google drive: {error}')
        else:
            print('no file found')

        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)

        done = False
        print(f'pulling {file_name} from google drive...')
        while done is False:
            status, done = downloader.next_chunk()
    except HttpError as error:
        print(f'google drive error: {error}')
        file = None

    file.seek(0) # after writing, pointer is at the end of the stream
    return pl.read_csv(file, separator=sep, infer_schema_length=100000).lazy()


def folder_id_from_name(service, folder_name:str, parent_id:str) -> str | None:
    '''
    returns the folder id of the folder_name in the parent folder
    '''
    try:
        results_folder = service.files().list(q=f"name = '{folder_name}' and '{parent_id}' in parents",
                                    supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
        folders = results_folder.get('files', [])
        if folders:
            folder_id = folders[0]['id']
        else:
            print('folder not found')
            folder_id = None

        return folder_id
    except HttpError as error:
        print(f'error checking google drive: {error}')
