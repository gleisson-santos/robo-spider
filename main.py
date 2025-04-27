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

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

# Adicionar middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo de dados para a requisição
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

# Armazenar clientes em um dicionário para gerenciar sessões
clients = {}

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
                await client(InviteToChannelRequest(target_entity, [user_to_add]))
                yield f"Adicionado: {member.username or member.first_name}\n"
                await asyncio.sleep(10)
            else:
                yield f"Usuário {member.username or member.first_name} é um bot ou inválido, pulando...\n"
        except Exception as e:
            yield f"Erro ao adicionar {member.username or member.first_name}: {e}\n"
            await asyncio.sleep(5)

async def process_account(account: Account, credentials: Credentials, source_groups: List[str], target_group: str, requires_code: bool = False):
    try:
        client = TelegramClient(account.session, int(credentials.api_id), credentials.api_hash)
        if not requires_code:
            clients[account.phone] = client  # Armazenar o cliente apenas na primeira tentativa

        client = clients[account.phone]
        await client.connect()

        if not await client.is_user_authorized():
            if not requires_code:
                yield f"Solicitando código de verificação para a conta {account.phone}\n"
                await client.send_code_request(account.phone)
                yield {"type": "code_request", "phone": account.phone}
                return  # Parar aqui e esperar o código
            else:
                yield f"Erro: Código de verificação já foi solicitado, mas a autenticação ainda não foi concluída para {account.phone}\n"
                return

        yield f"Conectado com a conta {account.phone}\n"

        for source_group in source_groups:
            source_entity = await client.get_entity(source_group)
            target_entity = await client.get_entity(target_group)
            yield f"Grupo de origem: {source_entity.title}, Grupo de destino: {target_entity.title}\n"

            members = []
            async for result in extract_members(client, source_entity):
                if isinstance(result, dict) and result.get("type") == "members":
                    members = result["data"]
                else:
                    yield result

            if members:
                async for log in add_members(client, target_entity, members):
                    yield log
            else:
                yield "Nenhum membro extraído\n"
    except Exception as e:
        yield f"Erro na conta {account.phone}: {e}\n"
    finally:
        # Não desconectar aqui; desconectar apenas após o processamento completo ou no submit-code
        pass

@app.post("/api/process")
async def process_request(request: ProcessRequest):
    if not request.accounts:
        raise HTTPException(status_code=400, detail="Pelo menos uma conta do Telegram é necessária.")
    if not request.sourceGroups:
        raise HTTPException(status_code=400, detail="Pelo menos um grupo de origem é necessário.")

    async def stream_logs():
        for account in request.accounts:
            async for log in process_account(account, request.credentials, request.sourceGroups, request.targetGroup):
                yield log
            # Não desconectar aqui; manter a sessão ativa até o submit-code ou o processamento completo
            yield f"Processamento concluído para a conta {account.phone}\n"
            await asyncio.sleep(30)

    return StreamingResponse(stream_logs(), media_type="text/plain")

@app.post("/api/submit-code")
async def submit_code(request: CodeRequest):
    phone = request.phone
    code = request.code

    if phone not in clients:
        raise HTTPException(status_code=400, detail="Nenhuma sessão ativa para este número de telefone.")

    client = clients[phone]
    async def stream_logs():
        try:
            yield f"Tentando autenticar a conta {phone} com o código {code}\n"
            await client.sign_in(phone, code)
            yield f"Autenticação bem-sucedida para a conta {phone}\n"

            # Após a autenticação bem-sucedida, continuar o processamento
            # Simular uma nova requisição para process_account, mas agora com requires_code=True
            dummy_credentials = Credentials(api_id="dummy", api_hash="dummy")  # Substituir por valores reais se necessário
            dummy_source_groups = ["@dummygroup"]  # Substituir por valores reais se necessário
            dummy_target_group = "@dummytarget"  # Substituir por valores reais se necessário
            async for log in process_account(
                Account(phone=phone, session=client.session.name),
                dummy_credentials,
                dummy_source_groups,
                dummy_target_group,
                requires_code=True
            ):
                yield log

        except PhoneCodeInvalidError:
            yield f"Erro: Código de verificação inválido para a conta {phone}\n"
        except SessionPasswordNeededError:
            yield f"Erro: Autenticação de dois fatores necessária para a conta {phone}. Isso não é suportado no momento.\n"
        except Exception as e:
            yield f"Erro ao autenticar a conta {phone}: {e}\n"
        finally:
            # Desconectar o cliente após o processamento ou erro
            if phone in clients:
                await clients[phone].disconnect()
                del clients[phone]

    return StreamingResponse(stream_logs(), media_type="text/plain")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
