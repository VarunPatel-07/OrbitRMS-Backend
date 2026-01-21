SIGN_IN_ERROR_MESSAGE = "Error accrued while signing in"
SIGN_IN_INVALID_CREDENTIALS = "Invalid Email Or Password"
SIGN_IN_ACCOUNT_INACTIVE = "Account is deactivated. Access denied."
SIGN_IN_ORG_INACTIVE = "Organization is deactivated. Access denied."
SIGN_IN_ORG_NOT_FOUND = "Organization not found"
SIGN_IN_RESET_LIMIT_EXCEEDED = "Reset limit exceeded. Please wait."

# ==== Admin Authentication Error Messages ====
ADMIN_SIGN_IN_ERROR_MESSAGE = "Error accrued while signing in as admin"
ADMIN_SIGN_IN_INVALID_CREDENTIALS = "Invalid Admin Email Or Password"
ADMIN_ACCOUNT_INACTIVE = "Admin account is deactivated. Access denied."
ADMIN_NOT_FOUND = "Admin not found"
ADMIN_RESET_LIMIT_EXCEEDED = "Reset limit exceeded. Please wait."
INVALID_OTP = "Invalid or expired OTP"
INSUFFICIENT_DATA = "Insufficient Data"

SOMETHING_WENT_WRONG = "Something went wrong. Please try again later."
# ==== General Error Messages ====
UNAUTHORIZED = "Unauthorized"
ACCESS_DENIED = "Access denied"
FILE_NOT_FOUND = "File not found"
UNAUTHORIZED_MISSING_TOKEN = "Unauthorized: Missing or invalid auth token"
UNAUTHORIZED_INVALID_TOKEN = "Unauthorized: Invalid or expired token"
INVALID_SESSION = "Invalid session"
INVALID_CREDENTIAL = "Invalid Credential"
USER_NOT_FOUND = "User Not Found"
ORGANIZATION_NOT_FOUND = "Organization Not Found"
NO_ORGANIZATIONS_FOUND = "No organizations found"
NO_SUCH_ORGANIZATION_FOUND = "No Such Organization Found"
NO_MAINTENANCE_LOGS_FOUND = "No Maintenance Logs Found"

# ==== Password Reset Error Messages ====
PASSWORD_RESET_LIMIT_EXCEEDED = "Reset limit exceeded. Please wait."
PASSWORD_RESET_LINK_INVALID = "This link is no longer valid. Please try again."
PASSWORD_SAME_AS_OLD = "New password must be different from the old one."
PASSWORD_RESET_IN_PROGRESS = (
    "You're currently resetting your password. Complete it before logging in."
)

# ==== Email Domain Error Messages ====
EMAIL_DOMAIN_ALREADY_IN_USE = "The Provided Email Domain Is Already In Use"
EMAIL_ALREADY_IN_USE = "The Provided Email Is Already In Use"

# ==== Employee Error Messages ====
EMPLOYEE_NOT_FOUND = "Employee Not Found"
EMPLOYEE_EMAIL_ALREADY_EXISTS = "The Employee With This Mail Already Exist"
EMPLOYEE_CODE_ALREADY_EXISTS = "The Employee With This Employee Code Exist"
REPORTING_MANAGER_REQUIRED = "Reporting manager is required"

# ==== Organization Error Messages (Additional) ====
ORGANIZATION_NOT_FOUND_CAPITALIZED = "Organization Not Found"

# ==== Client Inquiry Error Messages ====
CLIENT_INQUIRY_NOT_FOUND = "Client Inquiry Not Found"
UNABLE_TO_SUBMIT_INQUIRY = "Unable To Add Submit Inquiry Right Now"

# ==== Organization Error Messages ====
ORGANIZATION_CREATION_ERROR = "Error Accrued While Adding Employee"
ORGANIZATION_VERIFICATION_ERROR = "Error Accrued While Verifying The Meta Tag"

# ==== Password Error Messages ====
PASSWORD_CREATION_ERROR = "there was an error while creating a password"

# ==== Session Error Messages ====
SESSION_VERIFICATION_ERROR = "error while verifying user"
SESSION_DELETION_ERROR = "error while verifying user"
LOGOUT_ERROR = "Unable to log out the user at this moment."

# ==== Maintenance Mode Error Messages ====
MAINTENANCE_MODE_ACTIVE = "Maintenance Mode Is Active Now"

# ==== Meta Tag Error Messages ====
META_TAG_NOT_FOUND = "Meta Tag Not Found"

# ==== Email Error Messages ====
EMAIL_SEND_ERROR = "Error Accrued While Adding Employee"
PASSWORD_RESET_INSTRUCTION_ERROR = "Error Accrued While Password Reset Instruction"

# ==== Admin Verification Error Messages ====
ADMIN_VERIFICATION_ERROR = "error while Verifying Admin"

# ==== File/Directory Error Messages ====
INVALID_DIRECTORY_PATH = "The Provided Path Is Not A Valid Directory: {path}"

# ==== General Processing Error Messages ====
UNABLE_TO_FIND_USER = "Unable To Find User With This ID"
ERROR_WHILE_PROCESSING = "Error accrued while processing"


ERROR_WHILE_READING_FILE = "Error Accrued While Reading The Files"
ERROR_WHILE_READING_FOLDER = "Error Accrued While Reading The Backup Folder"
ERROR_READING_BACKUP_FOLDER = "Error Accrued While Reading The Backup Folder"
ERROR_WHILE_DOWNLOADING_FROM_BACKUP_FOLDER = "Error While Downloading File From The Backup Folder"
ERROR_IN_BULK_DOWNLOAD = "Error While bulk downloading files from the backup Folder"

ALREADY_VERIFIED = "Organization already Verified"

ERROR_WHILE_VERIFYING = "Error while verifying the organization"

ERROR_WHILE_ONBOARDING = "Error while onboarding the organization"

ERROR_WHILE_FETCHING_ORGANIZATION = "Error while fetching the organization info"


ERROR_WHILE_FETCHING_REPORTING_MANAGER = "Error while fetching All The Reporting Manager"

ERROR_WHILE_FETCHING_COUNTRY = "Error Accrued While Fetching The Country Contact Info"

NO_STATE_FOUND = "No states found for this country"

# ==== Client Inquiry Additional Error Messages ====
CLIENT_INQUIRE_NOT_FOUND = "Client Inquire Not Found"
INVALID_API_SECRET = "Invalid Api Secrete"
API_IS_DISABLED = "Api Is Disabled"
CONFIG_MODULE_NOT_FOUND = "Config Module Not Found"
FORM_ID_NOT_FOUND = "FormId Not Found"
MISSING_FIELDS_IN_PAYLOAD = "Missing fields in payload"
UNEXPECTED_FIELDS_IN_PAYLOAD = "Unexpected fields in payload"
MISSING_REQUIRED_FIELDS = "Missing required fields"
REQUIRED_FIELD_CANT_BE_NULL = "Required Field Can't Be Null"
NO_CITY_FOUND = "No city found for this state"
ERROR_WHILE_FETCHING_STATE_DATA = "error while fetching the state date of the country"
ERROR_FETCHING_DATA = "Error Fetching Data"

# ==== Feed/Post Error Messages ====
ONLY_ADD_OR_EDIT_ALLOWED = "Only Add Or Edit Is Allowed"
ID_REQUIRED_FOR_EDIT = "ID is required for edit operation"
POST_NOT_FOUND = "Post With This Id Not Found"
NOT_AUTHORIZED = "You Are Not Authorised"
ERROR_WHILE_POSTING = "error while Posting A Post"
INVALID_INPUT = "Invalid Input"
ERROR_WHILE_FETCHING_POSTS = "Error while Fetching Posts"
ERROR_WHILE_DELETING_POST = "Error while Deleting a Post"
ONLY_LIKE_OR_COMMENT_ALLOWED = "Only Like Or Comment Is Allowed"

# ==== Image Upload Error Messages ====
ERROR_WHILE_UPLOADING_IMAGE = "Error Accrued While Uploading Image"

# ==== Organization Additional Error Messages ====
ORGANIZATIONS_FETCHED_ERROR = "error while fetching organizations"
ERROR_WHILE_RESENDING_EMAIL_VERIFICATION = "error while Resending The Email Verification Link"
NO_ORGANIZATION_FOUND = "No Organization Found"
ERROR_WHILE_DELETING_ORGANIZATION = "Error While Deleting an Organization"
USERS_ORG_ID_MISMATCH = "User's org ID does not match."

# ==== Maintenance Mode Error Messages ====
INVALID_MAINTENANCE_TYPE = "Invalid type. Only 'activate' or 'deactivate' are allowed."
MAINTENANCE_SESSION_IN_PROGRESS = (
    "A maintenance session is already in progress. Please complete it before starting another."
)

REASON_IS_REQUIRED_FIELD = "The Reason Is An Required Field"
ENTER_VALID_DATE_DIFFERENCE = "Enter Valid Date Difference"
START_END_TIME_MINIMUM_APART = "Start and end time must be at least 30 minutes apart."
MAINTENANCE_DOES_NOT_EXIST = "Maintenance Dose Not Exist"
ERROR_WHILE_TOGGLING_MAINTENANCE = "error while toggling Maintenance Mode"
NO_MAINTENANCE_LOG_FOUND = "No Such Maintenance Log Found"
NO_MAINTENANCE_MODE_FOUND = "No Such Maintenance Mode Found"

# ==== Client Inquiry Additional Error Messages ====
UNABLE_TO_ENABLE_API = "Unable To Enable Api Right Now"
UNABLE_TO_DELETE_INQUIRY = "Unable Delete Inquiry Right Now"
UNABLE_TO_FIND_POST = "Unable To Find The Post"
UNABLE_TO_FIND_COMMENT = "Unable To Find The Comment"
ERROR_WHILE_LIKING_POST = "Error while liking/unliking post"
ERROR_WHILE_COMMENTING = "Error while adding comment"
ERROR_WHILE_HEALTH_CHECK = "An Error Accrued While Health Check"


INVALID_TYPE = "Invalid type. Must be 'add' or 'edit'"
PROJECT_STATUS_ALREADY_EXIST = "Project Status With This Name Is Already Exist"

PROJECT_STATUS_NOT_FOUND = "Project Status Not Found"
UNABLE_TO_UPDATE_PROJECT_STATUS = "Unable To Fetch Status Right Now"
UNABLE_TO_DELETE_PROJECT_STATUS = "Unable To Delete Status Right Now"

DEPARTMENT_ALREADY_EXISTS = "Department With This Name Already Exists"
DEPARTMENT_NOT_FOUND = "Department Not Found"
UNABLE_TO_UPDATE_DEPARTMENT = "Unable To Update Department Right Now"
UNABLE_TO_FETCH_DEPARTMENT = "Unable To Fetch Department Right Now"
DEPARTMENT_DELETED_SUCCESSFULLY = "Department Deleted Successfully"
UNABLE_TO_DELETE_DEPARTMENT = "Unable To Delete Department Right Now"

DESIGNATION_ALREADY_EXISTS = "Designation With This Name Already Exists"
DESIGNATION_NOT_FOUND = "Designation Not Found"
UNABLE_TO_UPDATE_DESIGNATION = "Unable To Update Designation Right Now"
UNABLE_TO_FETCH_DESIGNATION = "Unable To Fetch Designation Right Now"
UNABLE_TO_DELETE_DESIGNATION = "Unable To Delete Designation Right Now"

ERROR_WHILE_FETCHING_ROLES = "Error While Fetching Roles"

NO_MODULES_FOUND_FOR_ROLE = "No Modules Found For The Given Role"

ROLE_NOT_FOUND = "Role Not Found"

ERROR_WHILE_FETCHING_ROLES = "Error While Fetching Roles"
TYPE_MUST_BE_MODULE_OR_PERMISSION = "type should be module or permission"
MODULE_NOT_FOUND = "Module Not Found"
PERMISSION_NOT_FOUND = "Permission Not Found"

ERROR_WHILE_UPDATING_ROLE_PERMISSIONS = "Error While Updating The Role And Permission"
TYPE_MUST_BE_ADD_OR_EDIT = "The Type Should Be Add Edit"

CLONE_ROLE_ID_REQUIRED = "The Clone Role Id Is Required"
CONFIG_MODULE_ID_REQUIRED = "The Config Module Id Is Required"
DESIGNATIONS_ALREADY_EXISTS = "Designations Is Already Exist"
EDIT_ROLE_ID_REQUIRED = "The Edit Role Id Is Required"

NO_SUCH_ROLE_FOUND = "No Such Config Role Module Found"
FORM_ID_ALREADY_EXISTS = "Form ID Already Exist"
FORM_NOT_FOUND = "Form Not Found"
INQUIRY_FORM_UPDATED_SUCCESSFULLY = "Inquiry Form Updated Successfully"
UNABLE_TO_UPDATE_INQUIRY_FORM = "Unable To Update Inquiry Form Right Now"
EMPLOYEE_WITH_NAME_ALREADY_EXISTS = "Employee With This Name Already Exists"
ERROR_WHILE_ADDING_EMPLOYEE = "Error while Adding The Employee"
ERROR_WHILE_FETCHING_THE_USER_INFO = "Error while Fetching The User Info"
ID_REQUIRED_TO_EDIT_EMPLOYEE = "ID is required to edit employee"
EMPLOYEE_NAME_ALREADY_EXISTS = "Employee With This Name Already Exist"
ERROR_WHILE_EDITING_THE_USER = "Error while Editing the User"
ERROR_WHILE_FETCHING_ALL_THE_EMPLOYEE = "Error while Fetching All The Employee"
HOLIDAY_ALREADY_EXISTS = "Holiday With This Name Is Already Exist"
ID_REQUIRED_TO_OPERATION = "ID is required for edit operation"
HOLIDAY_NOT_FOUND = "Holiday Not Found"
INVALID_SORTING_ARGUMENT = "Invalid Sorting Argument"

UNABLE_TO_DELETE_HOLIDAY = "Unable To Delete Holiday"
LEAVE_TYPE_ALREADY_EXISTS = "Leave Type With This Name Or Code AllReady Exist"
UNABLE_TO_ADD_LEAVE_TYPE = "Unable Add Leave Type"
UNABLE_TO_ENABLE_API_RIGHT_NOW = "Unable To Enable Api Right Now"
INVALID_QUERY_ARGUMENT = "Invalid Query Argument"
UNABLE_TO_UPDATE_RECIPIENT_EMAIL = "Unable To Update Recipient Email Right Now"
ORGANIZATION_ALREADY_EXISTS = "The Provided Organization Name Is Already In Use"
FETCHING_EMPLOYEE = "error while fetching employee"
ERROR_WHILE_DISABLING_EMPLOYEE = "error while disabling/enabling employee"
INVALID_MAINTENANCE_MODE_TYPE = "Invalid type. Only 'activate' or 'deactivate' are allowed."
ERROR_WHILE_TOGGLING_MAINTENANCE_MODE = "error while toggling Maintenance Mode"
ERROR_WHILE_FETCHING_SOCIAL_ACCOUNTS = "An error occurred during Fetch Social Accounts"
NO_POST_FOUND = "No Post Found"
UNABLE_TO_FIND_SOCIAL_MEDIA_ACCOUNT = "Unable To Find SocialMedia Account"
ERROR_DURING_ORBIT_AI_CONVERSION = "An error occurred during The OrbitAi conversations"
ERROR_WHILE_APPLYING_LEAVE = "error while Fetching The User Info"
ERROR_WHILE_FETCHING_LEAVE_BALANCE = "Error while Fetching Leave Balance The User Info"
POST_WITH_THIS_ID_NOT_FOUND = "Post With This Id Not Found"
ERROR_WHILE_POSTING_POST = "error while Posting A Post"
ERROR_WHILE_UPLOADING_IMAGES = "Error Accrued While Uploading Image"
NO_LEAVE_TYPE_FOUND = "No Leave Type Found"
