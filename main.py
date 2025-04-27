from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import InputPeerUser
import asyncio
import logging
import csv
from typing import List, Dict
import io

# Configurar loggingghghg
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

# Modelo de dados para a requisição
class Account(BaseModel)
    phone str
    session str

class Credentials(BaseModel)
    api_id str
    api_hash str

class ProcessRequest(BaseModel)
    credentials Credentials
    accounts List[Account]
    sourceGroups List[str]
    targetGroup str

# Função para gerar logs em streaming
async def log_stream(message str)
    yield f{message}n

async def extract_members(client, source_entity)
    try
        members = await client.get_participants(source_entity, limit=10000)
        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerow(['User ID', 'Username', 'First Name', 'Last Name', 'Phone'])
        for member in members
            writer.writerow([
                member.id,
                member.username or '',
                member.first_name or '',
                member.last_name or '',
                member.phone or ''
            ])
        yield fTotal de membros extraídos {len(members)}n
        yield fMembros salvos em memórian
        return members
    except Exception as e
        yield fErro ao extrair membros {e}n
        return []

async def add_members(client, target_entity, members)
    for member in members
        try
            if not member.bot and member.id
                user_to_add = InputPeerUser(member.id, member.access_hash)
                await client(InviteToChannelRequest(target_entity, [user_to_add]))
                yield fAdicionado {member.username or member.first_name}n
                await asyncio.sleep(10)
        except Exception as e
            yield fErro ao adicionar {member.username or member.first_name} {e}n
            await asyncio.sleep(5)

async def process_account(account Account, credentials Credentials, source_groups List[str], target_group str)
    try
        client = TelegramClient(account.session, int(credentials.api_id), credentials.api_hash)
        await client.start(phone=account.phone)
        yield fConectado com a conta {account.phone}n

        for source_group in source_groups
            source_entity = await client.get_entity(source_group)
            target_entity = await client.get_entity(target_group)
            yield fGrupo de origem {source_entity.title}, Grupo de destino {target_entity.title}n

            members = []
            async for log in extract_members(client, source_entity)
                yield log
                if Total de membros extraídos in log
                    members = await client.get_participants(source_entity, limit=10000)

            if members
                async for log in add_members(client, target_entity, members)
                    yield log
            else
                yield Nenhum membro extraídon
    except Exception as e
        yield fErro na conta {account.phone} {e}n
    finally
        await client.disconnect()

@app.post(apiprocess)
async def process_request(request ProcessRequest)
    async def stream_logs()
        for account in request.accounts
            async for log in process_account(account, request.credentials, request.sourceGroups, request.targetGroup)
                yield log
            yield fProcessamento concluído para a conta {account.phone}n
            await asyncio.sleep(30)

    return StreamingResponse(stream_logs(), media_type=textplain)

if __name__ == __main__
    import uvicorn
    uvicorn.run(app, host=0.0.0.0, port=8000)
