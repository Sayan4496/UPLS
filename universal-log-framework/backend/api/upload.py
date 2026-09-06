from fastapi import APIRouter, UploadFile, File, HTTPException

from core.database import SessionLocal

from models.upload import Upload

from ingestion.validator import validate_file
from ingestion.file_handler import read_uploaded_file

from ingestion.processing_service import ProcessingService


router = APIRouter(

    prefix="/upload",

    tags=["Upload"]

)


@router.post("/")

async def upload_file(

    file: UploadFile = File(...)

):

    db = SessionLocal()


    try:


        # --------------------------------
        # STEP 1: Validate file
        # --------------------------------

        validate_file(
            file.filename
        )


        # --------------------------------
        # STEP 2: Read uploaded file
        # --------------------------------

        content = await read_uploaded_file(
            file
        )


        # --------------------------------
        # STEP 3: Determine file type
        # --------------------------------

        file_type = file.filename.split(
            "."
        )[-1].upper()


        # --------------------------------
        # STEP 4: Create upload record
        # --------------------------------

        upload = Upload(

            filename=file.filename,

            file_type=file_type

        )


        db.add(
            upload
        )

        db.commit()

        db.refresh(
            upload
        )


        # --------------------------------
        # STEP 5: Process file
        # --------------------------------

        processing_service = ProcessingService()


        result = processing_service.process(

            db=db,

            upload=upload,

            raw_content=content

        )


        # --------------------------------
        # STEP 6: Return response
        # --------------------------------

        return {

            "message":
                "File processed successfully",

            "upload_id":
                str(upload.id),

            "filename":
                upload.filename,

            "file_type":
                upload.file_type,

            "processing_result":
                result

        }


    except ValueError as e:


        db.rollback()


        raise HTTPException(

            status_code=400,

            detail=str(e)

        )


    except Exception as e:


        db.rollback()


        raise HTTPException(

            status_code=500,

            detail=str(e)

        )


    finally:


        db.close()