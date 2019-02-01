function openTab(evt, group, tabName) {
    // Declare all variables
    var i, tabcontent, tablinks;

    // Get all elements with class="tabcontent" and hide them
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
      if (tabcontent[i].id.startsWith(group)) {
        tabcontent[i].style.display = "none";
      }
    }

    // Get all elements with class="tablinks" and remove the class "active"
    tablinks = document.getElementsByClassName("tablinks");
    console.log('!! Assuming a one-to-one mapping of tablinks and tabcontent... if tabs are not working, you might want to check tabs.js');
    for (i = 0; i < tablinks.length; i++) {
      if (tabcontent[i].id.startsWith(group)) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
      }
    }

    // Show the current tab, and add an "active" class to the button that opened the tab
    document.getElementById(group + tabName).style.display = "block";
    evt.currentTarget.className += " active";
} 
