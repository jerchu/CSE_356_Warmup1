var board = [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '];

function make_move(num) {
    console.info("called");
    board[num - 1] = 'X';
    console.info(board)
    payload = JSON.stringify(
        {
            grid:board,
        }
    );
    $.ajax({
        url: "/ttt/play",
        type: 'POST',
        data: payload,
        dataType: 'json',
        contentType: "application/json",
        success: function(data){
            console.info(data.grid);
            board = data.grid;
            for(i = 0; i < board.length; i++){
                $("#"+(i+1)).text(board[i]);
                if(board[i] == "X" || board[i] == "O"){
                    $("#"+(i+1)).off("click");
                }
            }
            if(data.hasOwnProperty("winner")){
                if(data.winner == " "){
                    $("#winner").text("Tie");
                }
                else{
                    $("#winner").text(data.winner + " won");
                }
                $("#reset").show()
            }
        }
    });
}

function reset_board(){
    board = [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' '];
    for(i = 0; i < board.length; i++){
        $("#"+(i+1)).text(board[i]);
        $("#"+(i+1)).on("click");
    }
    $("#reset").hide()
    $("#winner").text("");
}
