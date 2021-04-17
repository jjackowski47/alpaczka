t = document.getElementsByClassName("offer-table")[0];


t.addEventListener("mouseenter", function(event){
    for ( let i = 1; i<t.rows.length; i++) {
        if(i%2==0) {
            t.rows[i].style.backgroundColor = "#5c616d";
        } else {
            t.rows[i].style.backgroundColor = "#3d4454"
        }
    }
});

t.addEventListener("mouseleave", function(event){
    for ( let i = 1; i<t.rows.length; i++) {
        if(i%2==0) {
            t.rows[i].style.backgroundColor = "#3d4454";
        } else {
            t.rows[i].style.backgroundColor = "#5c616d"
        }
    }
});