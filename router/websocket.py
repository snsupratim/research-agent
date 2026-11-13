from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict,List


router=APIRouter(tags=["websocktes"])

class ConnectionManager:
    def init__(self):
        self.active_connections: Dict[str,List[WebSocket]]={}


    async def connect(self, websocket:WebSocket,report_id:str):
        await websocket.accept()

        if report_id not in self.active_connections:
            self.active_connections[report_id]=[]

        self.active_connections[report_id].append(websocket)

    def disconnect(self, websocket:WebSocket,report_id:str):
        if report_id in self.active_connections:
            try:
                self.active_connections[report_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[report_id]:
                del self.active_connections[report_id]

    async def broadcast(self,report_id:str,message:dict):
        if report_id in self.active_connections:
            for connection in self.active_connections[report_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    print(f"Error sending message to websocket: {e}")
                    self.disconnect(connection,report_id)

manager=ConnectionManager()



@router.websocket("/reports/{report_id}/stream")
async def websocket_endpoint(websocket:WebSocket,report_id:str):
    await manager.connect(websocket,report_id)

    try:
        while True:
            data=await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket,report_id)
