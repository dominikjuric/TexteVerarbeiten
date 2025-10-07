"""
Zotero API integration for the knowledge pipeline.

This module provides a client for interacting with Zotero libraries via the Pyzotero API,
implementing the workflow described in the hybrid architecture document:
- Query items with /to_process tag
- Update item tags after processing (/to_process -> /processed)
- Extract PDFs and annotations for the pipeline
"""

import os
from pathlib import Path
from typing import List, Dict, Optional
import logging

try:
    from pyzotero import zotero  # type: ignore
    PYZOTERO_AVAILABLE = True
except ImportError:
    PYZOTERO_AVAILABLE = False
    zotero = None

logger = logging.getLogger(__name__)

# Constants for tag management
TAG_TO_PROCESS = '/to_process'
TAG_PROCESSED = '/processed'
TAG_ERROR = '/error'


class ZoteroClient:
    """
    Client for interacting with Zotero API following the hybrid pipeline workflow.
    
    This client implements the event-driven automation model using tags:
    - /to_process: Items waiting to be processed
    - /processed: Items that have been successfully processed  
    - /error: Items that failed processing
    """
    
    def __init__(self, library_id: str, library_type: str = 'user', api_key: Optional[str] = None):
        """
        Initialize Zotero client.
        
        Args:
            library_id: Zotero user ID or group ID
            library_type: 'user' or 'group' 
            api_key: Zotero API key (if None, reads from ZOTERO_API_KEY env var)
            
        Note:
            Get your API key from: https://www.zotero.org/settings/keys
            Get your user ID from: https://www.zotero.org/settings/keys (shown as userID)
        """
        if not PYZOTERO_AVAILABLE:
            raise ImportError("Pyzotero not available. Install with: pip install pyzotero")
            
        self.library_id = library_id
        self.library_type = library_type
        self.api_key = api_key or os.getenv('ZOTERO_API_KEY')
        
        if not self.api_key:
            raise ValueError("Zotero API key required. Set ZOTERO_API_KEY environment variable or pass api_key parameter.")
            
        # Initialize Pyzotero client
        self.zot = zotero.Zotero(library_id, library_type, self.api_key)
        
        # Test connection
        try:
            # Simple test call to verify credentials
            self.zot.key_info()
            logger.info(f"✅ Connected to Zotero {library_type} library: {library_id}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Zotero: {e}")
            raise
    
    def get_items_to_process(self, limit: int = 100) -> List[Dict]:
        """
        Get all items tagged with '/to_process' that need processing.
        
        Args:
            limit: Maximum number of items to retrieve
            
        Returns:
            List of Zotero item dictionaries with '/to_process' tag
        """
        try:
            # Search for items with the /to_process tag
            items = self.zot.items(tag=TAG_TO_PROCESS, limit=limit)
            logger.info(f"Found {len(items)} items to process")
            return items
        except Exception as e:
            logger.error(f"Error fetching items to process: {e}")
            return []
    
    def get_pdf_attachments(self, item_key: str) -> List[Dict]:
        """
        Get PDF attachments for a specific Zotero item.
        
        Args:
            item_key: Zotero item key
            
        Returns:
            List of PDF attachment dictionaries
        """
        try:
            # Get all children (attachments) of the item
            children = self.zot.children(item_key)
            
            # Filter for PDF attachments
            pdf_attachments = []
            for child in children:
                if (child.get('data', {}).get('contentType') == 'application/pdf' and 
                    child.get('data', {}).get('linkMode') in ['imported_file', 'imported_url']):
                    pdf_attachments.append(child)
            
            logger.debug(f"Found {len(pdf_attachments)} PDF attachments for item {item_key}")
            return pdf_attachments
            
        except Exception as e:
            logger.error(f"Error fetching PDF attachments for {item_key}: {e}")
            return []
    
    def download_pdf(self, attachment_key: str, output_dir: Path) -> Optional[Path]:
        """
        Download a PDF attachment from Zotero.
        
        Args:
            attachment_key: Zotero attachment key
            output_dir: Directory to save the PDF
            
        Returns:
            Path to downloaded PDF file, or None if download failed
        """
        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Get attachment info
            attachment = self.zot.item(attachment_key)
            filename = attachment['data'].get('filename', f"{attachment_key}.pdf")
            
            # Ensure .pdf extension
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
                
            output_path = output_dir / filename
            
            # Download the file
            with open(output_path, 'wb') as f:
                f.write(self.zot.file(attachment_key))
            
            logger.info(f"Downloaded PDF: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error downloading PDF {attachment_key}: {e}")
            return None
    
    def get_item_annotations(self, item_key: str) -> List[Dict]:
        """
        Get annotations (highlights, notes) for a Zotero item.
        
        Args:
            item_key: Zotero item key
            
        Returns:
            List of annotation dictionaries with extracted content
        """
        try:
            # Get all children including annotations
            children = self.zot.children(item_key)
            
            annotations = []
            for child in children:
                item_type = child.get('data', {}).get('itemType')
                if item_type == 'annotation':
                    annotation_data = {
                        'key': child['key'],
                        'type': child['data'].get('annotationType', 'unknown'),
                        'text': child['data'].get('annotationText', ''),
                        'comment': child['data'].get('annotationComment', ''),
                        'page': child['data'].get('annotationPageLabel', ''),
                        'color': child['data'].get('annotationColor', ''),
                        'tags': [tag['tag'] for tag in child['data'].get('tags', [])]
                    }
                    annotations.append(annotation_data)
            
            logger.debug(f"Found {len(annotations)} annotations for item {item_key}")
            return annotations
            
        except Exception as e:
            logger.error(f"Error fetching annotations for {item_key}: {e}")
            return []
    
    def mark_as_processed(self, item_key: str) -> bool:
        """
        Mark an item as processed by updating its tags.
        Removes '/to_process' tag and adds '/processed' tag.
        
        Args:
            item_key: Zotero item key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current item data
            item = self.zot.item(item_key)
            current_tags = item['data'].get('tags', [])
            
            # Update tags: remove /to_process, add /processed
            updated_tags = []
            for tag in current_tags:
                if tag['tag'] != TAG_TO_PROCESS:
                    updated_tags.append(tag)
            
            # Add /processed tag if not already present
            processed_tag_exists = any(tag['tag'] == TAG_PROCESSED for tag in updated_tags)
            if not processed_tag_exists:
                updated_tags.append({'tag': TAG_PROCESSED})
            
            # Update the item
            item['data']['tags'] = updated_tags
            self.zot.update_item(item)
            
            logger.info(f"✅ Marked item {item_key} as processed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error marking item {item_key} as processed: {e}")
            return False
    
    def mark_as_error(self, item_key: str, error_message: Optional[str] = None) -> bool:
        """
        Mark an item as having processing errors.
        Removes '/to_process' tag and adds '/error' tag.
        
        Args:
            item_key: Zotero item key
            error_message: Optional error description to add as note
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current item data
            item = self.zot.item(item_key)
            current_tags = item['data'].get('tags', [])
            
            # Update tags: remove /to_process, add /error
            updated_tags = []
            for tag in current_tags:
                if tag['tag'] != TAG_TO_PROCESS:
                    updated_tags.append(tag)
            
            # Add /error tag if not already present
            error_tag_exists = any(tag['tag'] == TAG_ERROR for tag in updated_tags)
            if not error_tag_exists:
                updated_tags.append({'tag': TAG_ERROR})
            
            # Update the item
            item['data']['tags'] = updated_tags
            self.zot.update_item(item)
            
            # Optionally add error note
            if error_message:
                try:
                    note_template = self.zot.item_template('note')
                    note_template['parentItem'] = item_key
                    note_template['note'] = f"<p><strong>Processing Error:</strong><br/>{error_message}</p>"
                    self.zot.create_items([note_template])
                except Exception as note_error:
                    logger.warning(f"Could not create error note: {note_error}")
            
            logger.warning(f"⚠️ Marked item {item_key} as error: {error_message}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error marking item {item_key} as error: {e}")
            return False
    
    def get_item_metadata(self, item_key: str) -> Dict:
        """
        Get comprehensive metadata for a Zotero item.
        
        Args:
            item_key: Zotero item key
            
        Returns:
            Dictionary with item metadata (title, authors, etc.)
        """
        try:
            item = self.zot.item(item_key)
            data = item['data']
            
            # Extract key metadata
            metadata = {
                'key': item_key,
                'title': data.get('title', 'Unknown Title'),
                'item_type': data.get('itemType', 'unknown'),
                'creators': [creator.get('name', f"{creator.get('firstName', '')} {creator.get('lastName', '')}").strip() 
                           for creator in data.get('creators', [])],
                'publication_year': data.get('date', '').split('-')[0] if data.get('date') else None,
                'journal': data.get('publicationTitle', ''),
                'doi': data.get('DOI', ''),
                'url': data.get('url', ''),
                'tags': [tag['tag'] for tag in data.get('tags', [])],
                'collections': data.get('collections', []),
                'date_added': data.get('dateAdded', ''),
                'date_modified': data.get('dateModified', '')
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error fetching metadata for {item_key}: {e}")
            return {'key': item_key, 'title': 'Error loading metadata'}


def create_zotero_client() -> Optional[ZoteroClient]:
    """
    Factory function to create a Zotero client from environment variables.
    
    Expects the following environment variables:
    - ZOTERO_USER_ID: Your Zotero user ID
    - ZOTERO_API_KEY: Your Zotero API key
    - ZOTERO_LIBRARY_TYPE: 'user' or 'group' (optional, defaults to 'user')
    - ZOTERO_GROUP_ID: Group ID if using group library (optional)
    
    Returns:
        ZoteroClient instance or None if configuration is missing
    """
    if not PYZOTERO_AVAILABLE:
        logger.error("Pyzotero not available. Install with: pip install pyzotero")
        return None
    
    # Get configuration from environment
    user_id = os.getenv('ZOTERO_USER_ID')
    api_key = os.getenv('ZOTERO_API_KEY') 
    library_type = os.getenv('ZOTERO_LIBRARY_TYPE', 'user')
    group_id = os.getenv('ZOTERO_GROUP_ID')
    
    if not api_key:
        logger.error("ZOTERO_API_KEY environment variable not set")
        return None
    
    # Determine library ID
    if library_type == 'group':
        if not group_id:
            logger.error("ZOTERO_GROUP_ID required for group libraries")
            return None
        library_id = group_id
    else:
        if not user_id:
            logger.error("ZOTERO_USER_ID environment variable not set")
            return None
        library_id = user_id
    
    try:
        return ZoteroClient(library_id, library_type, api_key)
    except Exception as e:
        logger.error(f"Failed to create Zotero client: {e}")
        return None


if __name__ == "__main__":
    """Test the Zotero client connection."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Test connection
    client = create_zotero_client()
    if client:
        print("✅ Zotero client created successfully")
        
        # Test basic functionality
        items = client.get_items_to_process(limit=5)
        print(f"Found {len(items)} items to process")
        
        if items:
            # Show first item details
            first_item = items[0]
            metadata = client.get_item_metadata(first_item['key'])
            print(f"Example item: {metadata['title']}")
    else:
        print("❌ Failed to create Zotero client")
        print("\nTo set up Zotero integration:")
        print("1. Get API key: https://www.zotero.org/settings/keys")
        print("2. Set environment variables:")
        print("   export ZOTERO_USER_ID='your_user_id'")
        print("   export ZOTERO_API_KEY='your_api_key'")