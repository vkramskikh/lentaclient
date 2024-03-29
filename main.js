function renderNewsItem(item) {
    var repr = $($('#template').html());
    $('td:first', repr).text(item.time);
    $('a.newslink', repr).text(item.title).attr('href', item.url);
    $('a.commentslink', repr).attr('href', item.url.replace('lenta.ru', 'readers.lenta.ru'));
    $('.item', repr).text(item.summary).click(function() {
        $(this).siblings('input').toggle().focus();
    });
    $('input', repr).keydown(function(event) {
        if (event.which == 13) {
            var input = $(this);
            var params = repr.data();

            if (params.posting) return;

            params.text = input.attr('value');
            input.attr('value', '');

            repr.data('posting', true);
            input.siblings('.posting').show();

            $.post('/comment/', params, function(data) {
                repr.data('posting', false);
                input.siblings('.posting').hide();

                var response = jQuery.parseJSON(data);
                if (response.status == 'ok') {
                    repr.data('parent_id', response.comment_id);
                } else if (response.status == 'error') {
                    alert(response.msg);
                }
            }).error(function() {
                alert("Error while posting");
                repr.data('posting', false);
                input.siblings('.posting').hide();
            });
        }
    });
    return repr;
}

function updateNewsList(item) {
    var matches = /\/news\/(.*?)\/$/.exec(item.url)
    var newsId = matches[1];
    var elId = newsId.replace(/\//g, '_');
    var el = $('#' + elId);
    if (!el.length) {
        var renderedItem = renderNewsItem(item);
        renderedItem.attr('id', elId);
        renderedItem.data('news_id', newsId);
        if (!firstRun) {
            renderedItem.css('background-color', 'yellow'); // highlight
            $.get('/count_comments/' + newsId, function(count) {
                $('a.commentslink', renderedItem).text(count);
            });
        }

        $('#news tbody').prepend(renderedItem);
        return true;
    } else {
        el.css('background-color', 'white');
        return false;
    }
}

function fetchNews() {
    $.getJSON('/news/', function(news) {
        var isUpdated = false;
        $.each(news, function(index, item) {
            isUpdated += updateNewsList(item);
        });

        if (isUpdated) {
            if (firstRun) {
                firstRun = false;
            } else {
                snd.currentTime = 0;
                snd.play();
            }
        }
    }).complete(function() {
        setTimeout(fetchNews, 10000)
    })
}

var firstRun = true;
var snd = new Audio('/static/notification.wav');
$(document).ready(fetchNews);
