@employee_router.post("/add", status_code=status.HTTP_200_OK)
@limiter.limit(API_RATE_LIMITING)
async def handle_add_user_function(
    request: Request,
    db: db_dependencies,
    data: AddEditUserProfileModel,
    background_task: BackgroundTasks,
    token: str = Depends(verify_token),
    organization_id: str = Query(..., alias="organization-id"),
):
    try:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Missing or invalid auth token", "success": False},
            )

        user_id = token["user_id"]
        session_id = token["session_id"]

        user = (
            db.query(Models.User)
            .options(joinedload(Models.User.sessions), joinedload(Models.User.organization))
            .filter(Models.User.id == user_id)
            .first()
        )

        if not user or not user.account_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": (
                        "Account is deactivated. Access denied."
                        if user.account_status
                        else "User Not Found"
                    ),
                    "success": False,
                },
            )

        if not user.organization.status:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Organization is deactivated. Access denied.", "success": False},
            )

        if not any(session.id == session_id for session in user.sessions):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"message": "Unauthorized: Invalid or expired token", "success": False},
            )

        organization_info = db.query(Models.Organization).filter_by(id=organization_id).first()
        if not organization_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "message": "Unable To Find The Organization With This ID",
                    "success": False,
                },
            )

        normalized_full_name = " ".join(data.personal_info.full_name.strip().split()).lower()

        # Validations
        if (
            db.query(Models.PersonalInfo)
            .join(Models.User)
            .filter(
                func.lower(Models.PersonalInfo.full_name) == normalized_full_name,
                Models.User.organization_id == organization_id,
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "Employee With This Name Already Exist", "success": False},
            )

        if (
            db.query(Models.EmployeeInfo)
            .join(Models.User)
            .filter(
                Models.EmployeeInfo.email == data.employee_info.employee_email,
                Models.User.organization_id == organization_id,
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "The Employee With This Mail Already Exist", "success": False},
            )

        if (
            db.query(Models.EmployeeInfo)
            .join(Models.User)
            .filter(
                Models.EmployeeInfo.employee_code == data.employee_info.employee_code,
                Models.User.organization_id == organization_id,
            )
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"message": "The Employee With This Employee Code Exist", "success": False},
            )

        hash_password = hash_passwords(SUPER_SECURE_HASH_PASSWORD)

        with db.begin():
            # Create user
            new_user = Models.User(password=hash_password, organization_id=organization_id)
            db.add(new_user)
            db.flush()

            # Personal Info
            personal_info = create_model_instance(
                model=Models.PersonalInfo, data=data.personal_info, fields=["-user_id"]
            )
            personal_info.user_id = new_user.id
            db.add(personal_info)

            # Validate reporting manager
            reporting_to_user = (
                db.query(Models.User)
                .filter(Models.User.id == data.employee_info.reporting_to.id)
                .first()
            )
            if not reporting_to_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": f"Reporting to user ID {data.employee_info.reporting_to.id} does not exist.",
                        "success": False,
                    },
                )

            employee_info_data = data.employee_info.dict(exclude={"employee_role", "reporting_to"})
            employee_info = create_model_instance(
                model=Models.EmployeeInfo,
                data=employee_info_data,
                fields=["-employee_role_id", "-user_id", "-reporting_to_id"],
            )
            employee_info.user_id = new_user.id
            employee_info.employee_role_id = data.employee_info.employee_role.role_id
            employee_info.reporting_to_id = data.employee_info.reporting_to.id
            db.add(employee_info)

            # Personal Contact Info
            pci_data = data.personal_contact_info.dict(exclude={"emergency_contacts"})
            pci = create_model_instance(
                model=Models.PersonalContactInfo, data=pci_data, fields=["-user_id"]
            )
            pci.user_id = new_user.id
            db.add(pci)
            db.flush()

            # Emergency Contacts
            emergency_contacts = [
                create_model_instance(
                    model=Models.EmergencyContact, data=contact, fields=["-contact_id", "-id"]
                )
                for contact in data.personal_contact_info.emergency_contacts
            ]
            for contact in emergency_contacts:
                contact.contact_id = pci.id
            db.add_all(emergency_contacts)

            # Family Info
            family_info_data = data.family_info.dict(exclude={"children"})
            family_info = create_model_instance(
                model=Models.FamilyInfo, data=family_info_data, fields=["-user_id"]
            )
            family_info.user_id = new_user.id
            db.add(family_info)
            db.flush()

            if data.family_info.marital_status in alignable_for_child_info:
                children = [
                    create_model_instance(
                        model=Models.Children, data=child, fields=["-family_info_id"]
                    )
                    for child in data.family_info.children
                ]
                for child in children:
                    child.family_info_id = family_info.id
                db.add_all(children)

            # Addresses
            current_address = create_model_instance(model=Models.Address, data=data.current_address)
            db.add(current_address)
            db.flush()
            new_user.current_address_id = current_address.id
            new_user.same_as_current_address = data.same_as_current_address

            if not data.same_as_current_address:
                permanent_address = create_model_instance(
                    model=Models.Address, data=data.permanent_address
                )
                db.add(permanent_address)
                db.flush()
                new_user.permanent_address_id = permanent_address.id

            # Social Links
            social_links = [
                create_model_instance(
                    model=Models.SocialLinks, data=link, fields=["-user_id", "-id"]
                )
                for link in data.social_link
                if link.name and link.link and link.icon
            ]
            for link in social_links:
                link.user_id = new_user.id
            db.add_all(social_links)

            # Finalize user with reset token
            reset_password_token = generatePasswordResetToken()
            new_user.reset_password_token = reset_password_token

        # Outside of transaction
        encrypted_user_id = urlsafe_data_encoding_function(new_user.id)
        encrypted_token = urlsafe_data_encoding_function(reset_password_token)

        email_data = {
            "recever_email": data.employee_info.employee_email,
            "subject": f"Welcome {data.personal_info.full_name} to {organization_info.general_info.organization_name} – We're excited to have you onboard!",
            "body": WelcomeMailForNewlyAddedEmployee(
                WelcomeEmployeeMailModel(
                    **{
                        "user_name": data.personal_info.full_name,
                        "organization_name": organization_info.general_info.organization_name,
                        "create_password_link": f"{FRONTEND_URL}/auth/create-password?user-id={encrypted_user_id}&token={encrypted_token}",
                    }
                )
            ),
        }

        email_instance = EmailSchema(**email_data)
        email_sender_function(email_instance, background_task)

        return {"message": "successfully added the user", "success": True}

    except HTTPException as http_exception:
        raise http_exception
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "error while Adding The User", "error": str(e), "success": False},
        )
