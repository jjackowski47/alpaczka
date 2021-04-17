
const GET = "GET";
const POST = "POST";
const URL = "https://localhost";
const LOGIN_FIELD_ID = "login";
const PASSWORD_FIELD_ID = "password";
const REPEAT_PASSWORD_FIELD_ID = "second_password";
const REGISTRATION_FORM_ID = "registration-form"
var isLoginTaken = false;

var HTTP_STATUS = { OK: 200, CREATED: 201, NOT_FOUND: 404 };

let registrationForm = document.getElementById(REGISTRATION_FORM_ID);
let loginInputField = document.getElementById(LOGIN_FIELD_ID);
let repeatPasswordField = document.getElementById(REPEAT_PASSWORD_FIELD_ID);
let passwordInputField = document.getElementById(PASSWORD_FIELD_ID);

loginInputField.addEventListener("change", updateLoginAvailabilityMessage);
repeatPasswordField.addEventListener("change", repeatPasswordCorrect);
registrationForm.addEventListener("submit", function (event) {
        
    if (!repeatPasswordCorrect()){
        event.preventDefault();
        showWarningMessage("wrong-data", "Błędne dane", "button-reg-form");
    } else if (isLoginTaken){
        event.preventDefault();
        showWarningMessage("wrong-login", "Ten login jest już zajęty", LOGIN_FIELD_ID);
        showWarningMessage("wrong-data", "Błędne dane", "button-reg-form");
    } else {
        removeWarningMessage("wrong-login");
        removeWarningMessage("wrong-data");
    }
});


function updateLoginAvailabilityMessage() {
    let warningElemId = "wrong-login";
    let warningMessage = "Ten login jest już zajęty";

    isLoginAvailable().then(function (isAvailable) {
        if (isAvailable) {
            isLoginTaken=false;
            removeWarningMessage(warningElemId);
        } else {
            isLoginTaken=true;
            showWarningMessage(warningElemId, warningMessage, LOGIN_FIELD_ID);
        }
    }).catch(function (error) {
        console.error("Something went wrong while checking login.");
        console.error(error);
    });
}

function isLoginAvailable() {
    return Promise.resolve(checkLoginAvailability().then(function (statusCode) {
        if (statusCode === HTTP_STATUS.OK) {
            return false;
        } else if (statusCode === HTTP_STATUS.NOT_FOUND) {
            return true
        } else {
            throw "Unknown login availability status: " + statusCode;
        }
    }));
}

function checkLoginAvailability() {
    let baseUrl = URL + ":7000/user/";
    let userUrl = baseUrl + loginInputField.value;

    return Promise.resolve(fetch(userUrl, { method: GET }).then(function (resp) {
        return resp.status;
    }).catch(function (err) {
        return err.status;
    }));
}

function removeWarningMessage(warningElemId) {
    let warningElem = document.getElementById(warningElemId);

    if (warningElem !== null) {
        warningElem.remove();
    }
}

function showWarningMessage(newElemId, message, FIELD_ID) {
    let warningElem = prepareWarningElem(newElemId, message);
    appendAfterElem(FIELD_ID, warningElem);
}

function prepareWarningElem(newElemId, message) {
    let warningField = document.getElementById(newElemId);

    if (warningField === null) {
        let textMessage = document.createTextNode(message);
        warningField = document.createElement('span');
        warningField.appendChild(textMessage);
        warningField.style.fontSize = "10.5px";
        warningField.style.color = "red";

        
        warningFieldRow = document.createElement('li');
        warningFieldRow.className = "form-row";
        warningFieldRow.setAttribute("id", newElemId);

        warningFieldRow.appendChild(warningField);

        warningField.className = "warning-field";
    }
    return warningFieldRow;
}

function appendAfterElem(currentElemId, newElem) {
    let currentElem = document.getElementById(currentElemId).parentElement;
    currentElem.insertAdjacentElement('afterend', newElem);
}



function checkRegistrationStatus() {
    let registerUrl = URL + "register";
    let registerParams = {
        method: POST,
        body: new FormData(registrationForm),
        redirect: "follow"
    };
    
    fetch(registerUrl, registerParams)
                .then(response => getRegisterResponseData(response))
                .catch(err => {
                    console.log("Caught error: " + err);
                });
}

function getRegisterResponseData(response) {
    let status = response.status;

    if (status === HTTP_STATUS.OK || status === HTTP_STATUS.CREATED) {
        removeWarningMessage("register-status");
        showWarningMessage("register-status","Zarejestrowano pomyślnie", "button-reg-form")
        return response.json();
    } else {
        removeWarningMessage("register-status");
        showWarningMessage("register-status","Wystąpił błąd podczas rejestracji", "button-reg-form")
        console.error("Response status code: " + response.status);
        throw "Unexpected response status: " + response.status;
    }
}


function repeatPasswordCorrect() {
    if (repeatPasswordField.value != passwordInputField.value) {
        showWarningMessage("wrong-repeat", "Wprowadzone hasła nie zgadzają się.", REPEAT_PASSWORD_FIELD_ID);
        return false;
    } else {
        removeWarningMessage("wrong-repeat");
        return true;
    }
}

