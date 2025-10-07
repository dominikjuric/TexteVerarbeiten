from dotenv import load_dotenv
import os
load_dotenv()
CFG = {
  "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
  "MATHPIX_APP_ID": os.getenv("MATHPIX_APP_ID"),
  "MATHPIX_APP_KEY": os.getenv("MATHPIX_APP_KEY"),
  "ZOTERO_USER_ID": os.getenv("ZOTERO_USER_ID"),
  "ZOTERO_API_KEY": os.getenv("ZOTERO_API_KEY"),
}
