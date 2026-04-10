
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.config import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        user_name: str = payload.get("name") 
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="التوكن غير صالح")
            
        return {"user_id": int(user_id), "name": user_name}
    except JWTError:
        raise HTTPException(status_code=401, detail="انتهت جلسة العمل، سجل دخول تاني")