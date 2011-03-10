$(function(){
        $('body').append('<div id="tooltip" />');
        $('.provInfo').tooltip(
        {
                position:     'bottom right',
                offset:       [0, 5],
                delay:        100,
                effect:       'fade',
                tip:          '#tooltip',
                onBeforeShow: function(e) {
                        match = this.getTrigger().attr("id").match(/^hover_(\ws+)$/);
                        id = "info_"+this.getTrigger().attr("id");
                        info = $("#"+id).html();
                        $('#tooltip').html(info);
                }
        })
})
