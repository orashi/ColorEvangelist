//首屏自适应高度
var resize_first_screen_to_window_height = function () {
    var h = window.innerHeight || document.body.clientHeight || document.documentElement.clientHeight;
    $(".bg-attachment1 .bg-attachment-hidden").css("height", h);
};

$(window).on("resize", resize_first_screen_to_window_height);


var scroll_to_smoothly_generator = function ($target) {
    return function(){
        $('html,body').animate({scrollTop: $target.offset().top}, 800);
    }
};

$(document).ready(function () {
    resize_first_screen_to_window_height();

    var scroll_to_start = scroll_to_smoothly_generator($("#start"));
    //start按钮滚动到指定位置
    var $img_start_button = $("#img_start_button");
    var $txt_start_button = $("#txt_start_button");

    $img_start_button.click(scroll_to_start);
    $txt_start_button.click(scroll_to_start);
    $("#img_down_arrow").click(scroll_to_start);

    $("ul.nav a").click(function (e) {
        e.preventDefault();
        scroll_to_smoothly_generator($($(this).attr("href")))();
    });


    //start button hover
    var img_start_button_hover = function () {
        $img_start_button.css("background","url(imgs/start_button_hover.png) no-repeat center center");
        $img_start_button.css("background-size","95% 95%");
    };

    var img_start_button_hover_out = function () {
        $img_start_button.css("background","url(imgs/start_button.png) no-repeat center center");
        $img_start_button.css("background-size","95% 95%");
    };
    $img_start_button.hover(img_start_button_hover,img_start_button_hover_out);
    $txt_start_button.hover(img_start_button_hover,img_start_button_hover_out);
});