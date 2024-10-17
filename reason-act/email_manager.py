import os
import json

# delete later 
from colorama import Fore

class EmailManager:
    def __init__(self):
        self.drafts_folder = 'reason-act/email_drafts'
        self._ensure_drafts_folder_exists()
        self.draft_counter = self._get_latest_draft_id()

    def _ensure_drafts_folder_exists(self):
        if not os.path.exists(self.drafts_folder):
            os.makedirs(self.drafts_folder)

    def _get_latest_draft_id(self):
        draft_files = [f for f in os.listdir(self.drafts_folder) if f.endswith('.json')]
        if not draft_files:
            return 0
        return max([int(f.split('_')[1].split('.')[0]) for f in draft_files]) + 1

    def _get_draft_path(self, draft_id):
        return os.path.join(self.drafts_folder, f'draft_{draft_id}.json')

    def write_email(self, to: str, subject: str, body: str, draft_id: str | None = None):
        print(Fore.RED + "DEBUGGING; write_email called with to:", to, "subject:", subject, "body:", body, "draft_id:", draft_id)
        if draft_id is None:
            draft_id = f"draft_{self.draft_counter}"
            self.draft_counter += 1
        else:
            draft_id = draft_id.strip()

        draft_path = self._get_draft_path(draft_id.split('_')[1])
        draft_content = {
            'to': to,
            'subject': subject,
            'body': body
        }

        with open(draft_path, 'w') as f:
            json.dump(draft_content, f, indent=2)

        return draft_id

    def get_draft(self, draft_id: str):
        draft_path = self._get_draft_path(draft_id.split('_')[1])
        if os.path.exists(draft_path):
            with open(draft_path, 'r') as f:
                return json.load(f)
        else:
            return {}

    def update_draft(self, draft_id: str, field: str, new_content: str):
        draft_path = self._get_draft_path(draft_id.split('_')[1])
        if os.path.exists(draft_path) and field in ['to', 'subject', 'body']:
            with open(draft_path, 'r+') as f:
                draft = json.load(f)
                draft[field] = new_content
                f.seek(0)
                json.dump(draft, f, indent=2)
                f.truncate()
            return True
        return False

    def delete_draft(self, draft_id: str):
        draft_path = self._get_draft_path(draft_id.split('_')[1])
        if os.path.exists(draft_path):
            os.remove(draft_path)
            return True
        return False

    def list_drafts(self, amount: int) -> list[dict]:
        draft_files = sorted([f for f in os.listdir(self.drafts_folder) if f.endswith('.json')])
        drafts = []
        for draft_file in draft_files[:amount]:
            draft_id = draft_file.split('.')[0]
            with open(os.path.join(self.drafts_folder, draft_file), 'r') as f:
                draft_content = json.load(f)
                drafts.append({"id": draft_id, **draft_content})
        return drafts
