from mangum import Mangum

from deadresult.api.app import app

handler = Mangum(app, lifespan="off")
