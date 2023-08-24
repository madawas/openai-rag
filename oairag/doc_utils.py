import logging
import os

from pypdf import PdfReader
from tenacity import retry, stop_after_attempt, wait_random_exponential
from oairag.config import settings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings

LOG = logging.getLogger(__name__)
EMBEDDINGS = OpenAIEmbeddings()


def process_document(filename: str, form_recognizer=None):
    LOG.debug(f"Processing document: {filename}")
    page_map = get_document_text(filename, form_recognizer)
    LOG.debug(f"{filename} processing complete")


def get_document_text(filename: str, form_recognizer=None) -> list:
    offset = 0
    page_map = []
    if form_recognizer:
        LOG.error("Form Recognizer is not supported")
        # todo: implement form recognizer support
        # https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/scripts/prepdocs.py
        # #L113-L146
        reader = PdfReader(os.path.join(settings.doc_upload_dir, filename))
        pages = reader.pages
        for page_num, p in enumerate(pages):
            page_text = p.extract_text()
            page_map.append((page_num, offset, page_text))
            offset += len(page_text)
    else:
        reader = PdfReader(os.path.join(settings.doc_upload_dir, filename))
        pages = reader.pages
        for page_num, p in enumerate(pages):
            page_text = p.extract_text()
            page_map.append((page_num, offset, page_text))
            offset += len(page_text)
    LOG.debug(page_map)
    return page_map


def split_text(page_map):
    sentence_endings = [".", "!", "?"]
    words_breaks = [",", ";", ":", " ", "(", ")", "[", "]", "{", "}", "\t", "\n"]

    def find_page(offset):
        num_pages = len(page_map)
        for i in range(num_pages - 1):
            if page_map[i][1] <= offset < page_map[i + 1][1]:
                return i
        return num_pages - 1

    all_text = "".join(p[2] for p in page_map)
    length = len(all_text)
    start = 0
    end = length
    while start + settings.chunk_overlap < length:
        last_word = -1
        end = start + settings.chunk_length

        if end > length:
            end = length
        else:
            # Try to find the end of the sentence
            while end < length and (
                    end - start - settings.chunk_length) < settings.sentence_search_limit and \
                    all_text[end] not in sentence_endings:
                if all_text[end] in words_breaks:
                    last_word = end
                end += 1
            if end < length and all_text[end] not in sentence_endings and last_word > 0:
                end = last_word  # Fall back to at least keeping a whole word
        if end < length:
            end += 1

        # Try to find the start of the sentence or at least a whole word boundary
        last_word = -1
        while start > 0 and start > end - settings.chunk_length - 2 * \
                settings.sentence_search_limit and all_text[start] not in sentence_endings:
            if all_text[start] in words_breaks:
                last_word = start
            start -= 1
        if all_text[start] not in sentence_endings and last_word > 0:
            start = last_word
        if start > 0:
            start += 1

        section_text = all_text[start:end]
        yield section_text, find_page(start)

        last_table_start = section_text.rfind("<table")
        if (
                last_table_start > 2 * settings.sentence_search_limit and last_table_start >
                section_text.rfind(
                "</table")):
            # If the section ends with an unclosed table, we need to start the next section with
            # the table.
            # If table starts inside SENTENCE_SEARCH_LIMIT, we ignore it, as that will cause an
            # infinite loop for tables longer than MAX_SECTION_LENGTH
            # If last table starts inside SECTION_OVERLAP, keep overlapping
            LOG.debug(f"Section ends with unclosed table, starting next section with the table at "
                      f"page {find_page(start)} offset {start} table start {last_table_start}")
            start = min(end - settings.chunk_overlap, start + last_table_start)
        else:
            start = end - settings.chunk_overlap

    if start + settings.chunk_overlap < end:
        yield all_text[start:end], find_page(start)



# @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(15), before_sleep=before_retry_sleep)
# def compute_embedding(text):
#     refresh_openai_token()
#     return openai.Embedding.create(engine=args.openaideployment, input=text)["data"][0]["embedding"]


