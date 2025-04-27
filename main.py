from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import InputPeerUser
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
import asyncio
import logging
import csv
from typing import List
import io
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Account(BaseModel):
    phone: str
    session: str

class Credentials(BaseModel):
    api_id: str
    api_hash: str

class ProcessRequest(BaseModel):
    credentials: Credentials
    accounts: List[Account] = []
    sourceGroups: List[str] = []
    targetGroup: str

class CodeRequest(BaseModel):
    phone: str
    code: str
    credentials: Credentials
    sourceGroups: List[str]
    targetGroup: str

pending_sessions = {}

async def log_stream(message: str):
    yield f"{message}\n"

async def extract_members(client, source_entity):
    try:
        members = await client.get_participants(source_entity, limit=10000)
        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerow(['User ID', 'Username', 'First Name', 'Last Name', 'Phone'])
        for member in members:
            writer.writerow([
                member.id,
                member.username or '',
                member.first_name or '',
                member.last_name or '',
                member.phone or ''
            ])
        yield f"Total de membros extraídos: {len(members)}\n"
        yield f"Membros salvos em memória\n"
        yield {"type": "members", "data": members}
    except Exception as e:
        yield f"Erro ao extrair membros: {e}\n"
        yield {"type": "members", "data": []}

async def add_members(client, target_entity, members):
    for member in members:
        try:
            if not member.bot and member.id:
                user_to_add = InputPeerUser(member.id, member.access_hash)
                await client(InviteToChannelRequest(target_entity
