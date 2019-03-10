(function(){
    $(document).ready(function () {
        $("#image-query-form").submit(function(e) {
            e.preventDefault(); // avoid to execute the actual submit of the form.

            var form = $(this);
            var url = form.attr('action');
            var data = new FormData(this);
            jQuery.each($("#image-query-form")[0][0].files, function(i, file) {
                data.append('file', file);
            });

            $.ajax({
               type: "POST",
               url: url,
               data: data,
               enctype: 'multipart/form-data',
               processData: false,
               contentType: false,
               cache: false,
               success: function(data)
               {
                   $('#disp-id').text(data['idx']);
                   $('#disp-dist').text(data['dist']);
                   $('#disp-img').html("<img src='" + data['wat_path'] + "' alt='waterfall'/>");
                   $('#results').show();
               }
             });
        });
    });
})()