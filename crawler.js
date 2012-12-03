/*
 * this file is used to fill forms for evaluating our system
 */

function submitForm() {
  for (var i = 0; i < document.forms.length; i++) {
    for (var j = 0; j < document.forms[i].length; j++) {
      var elem = document.forms[i].elements[j];
      if (elem.type == "submit") {
        document.forms[i].submit();
        return;
      }
    }
  }
}

function fillFormElements() {
  for (var i = 0; i < document.forms.length; i++) {
    for (var j = 0; j < document.forms[i].length; j++) {
      var elem = document.forms[i].elements[j];
      if (elem.type == "text" || elem.type == "password") {
        elem.value = "jsflow_"+i+"_"+j;
      }
    }
  }
  submitForm();
}

window.onload = fillFormElements;
